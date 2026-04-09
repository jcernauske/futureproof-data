"""Tests for O*NET ingestors.

Sample data is extracted from the real O*NET 30.2 database files.
Career Changers Matrix and Career Starters Matrix are not available
in O*NET 30.2 and are excluded.
"""

from pathlib import Path

from pyiceberg.schema import Schema

from raw.onet_ingestor import (
    OnetBaseIngestor,
    OnetOccupationsIngestor,
    OnetRelatedOccupationsIngestor,
    OnetTaskStatementsIngestor,
    OnetWorkActivitiesIngestor,
    OnetWorkContextIngestor,
)

SAMPLES_DIR = Path(__file__).parent / "onet_samples"


def _make(cls):
    """Create an ingestor instance without requiring real config objects."""
    obj = cls.__new__(cls)
    return obj


def _fetch_sample(ingestor):
    """Run fetch() with the local sample cache dir and return the raw rows."""
    entities = {"onet": "O*NET Test"}
    result = ingestor.fetch(entities, "bulk_zip_download", cache_dir=str(SAMPLES_DIR))
    return result["onet"]


# ============================================================
# Schema Tests
# ============================================================


class TestOccupationsSchema:
    def test_returns_iceberg_schema(self):
        ingestor = _make(OnetOccupationsIngestor)
        assert isinstance(ingestor.get_schema(), Schema)

    def test_has_grain_field(self):
        ingestor = _make(OnetOccupationsIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        assert "onet_soc_code" in names

    def test_has_metadata_fields(self):
        ingestor = _make(OnetOccupationsIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        for meta in ("ingested_at", "source_url", "source_method", "load_date"):
            assert meta in names

    def test_field_count(self):
        """3 data fields + 4 metadata = 7."""
        ingestor = _make(OnetOccupationsIngestor)
        assert len(ingestor.get_schema().fields) == 7


class TestTaskStatementsSchema:
    def test_returns_iceberg_schema(self):
        ingestor = _make(OnetTaskStatementsIngestor)
        assert isinstance(ingestor.get_schema(), Schema)

    def test_has_grain_fields(self):
        ingestor = _make(OnetTaskStatementsIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        assert "onet_soc_code" in names
        assert "task_id" in names

    def test_field_count(self):
        """7 data fields + 4 metadata = 11."""
        ingestor = _make(OnetTaskStatementsIngestor)
        assert len(ingestor.get_schema().fields) == 11


class TestWorkActivitiesSchema:
    def test_returns_iceberg_schema(self):
        ingestor = _make(OnetWorkActivitiesIngestor)
        assert isinstance(ingestor.get_schema(), Schema)

    def test_has_grain_fields(self):
        ingestor = _make(OnetWorkActivitiesIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        for g in ("onet_soc_code", "element_id", "scale_id"):
            assert g in names

    def test_field_count(self):
        """13 data fields + 4 metadata = 17."""
        ingestor = _make(OnetWorkActivitiesIngestor)
        assert len(ingestor.get_schema().fields) == 17

    def test_no_category_field(self):
        ingestor = _make(OnetWorkActivitiesIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        assert "category" not in names


class TestWorkContextSchema:
    def test_returns_iceberg_schema(self):
        ingestor = _make(OnetWorkContextIngestor)
        assert isinstance(ingestor.get_schema(), Schema)

    def test_has_category_field(self):
        ingestor = _make(OnetWorkContextIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        assert "category" in names

    def test_field_count(self):
        """14 data fields + 4 metadata = 18."""
        ingestor = _make(OnetWorkContextIngestor)
        assert len(ingestor.get_schema().fields) == 18


class TestRelatedOccupationsSchema:
    def test_has_is_primary(self):
        ingestor = _make(OnetRelatedOccupationsIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        assert "is_primary" in names
        assert "related_index" in names

    def test_has_relatedness_tier(self):
        ingestor = _make(OnetRelatedOccupationsIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        assert "relatedness_tier" in names

    def test_field_count(self):
        """5 data + 4 metadata = 9."""
        ingestor = _make(OnetRelatedOccupationsIngestor)
        assert len(ingestor.get_schema().fields) == 9


# ============================================================
# Constants Tests
# ============================================================


class TestConstants:
    def test_download_url(self):
        assert "onetcenter.org" in OnetBaseIngestor.DOWNLOAD_URL
        assert OnetBaseIngestor.DOWNLOAD_URL.endswith(".zip")

    def test_cache_dir(self):
        assert OnetBaseIngestor.CACHE_DIR == "data/raw/onet_cache"

    def test_user_agent_is_browser_like(self):
        assert "Mozilla" in OnetBaseIngestor.USER_AGENT

    def test_source_filenames(self):
        assert OnetOccupationsIngestor.SOURCE_FILENAME == "Occupation Data.txt"
        assert OnetTaskStatementsIngestor.SOURCE_FILENAME == "Task Statements.txt"
        assert OnetWorkActivitiesIngestor.SOURCE_FILENAME == "Work Activities.txt"
        assert OnetWorkContextIngestor.SOURCE_FILENAME == "Work Context.txt"
        assert OnetRelatedOccupationsIngestor.SOURCE_FILENAME == "Related Occupations.txt"


# ============================================================
# Fetch Tests
# ============================================================


class TestFetchOccupations:
    def test_returns_dict(self):
        ingestor = _make(OnetOccupationsIngestor)
        result = ingestor.fetch({"onet": "test"}, "test", cache_dir=str(SAMPLES_DIR))
        assert isinstance(result, dict)
        assert "onet" in result

    def test_returns_rows(self):
        ingestor = _make(OnetOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        assert isinstance(rows, list)
        assert len(rows) == 5

    def test_rows_are_dicts(self):
        ingestor = _make(OnetOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        assert all(isinstance(r, dict) for r in rows)

    def test_soc_code_preserved_as_string(self):
        ingestor = _make(OnetOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        for row in rows:
            soc = row["O*NET-SOC Code"]
            assert isinstance(soc, str)
            assert "." in soc


class TestFetchTaskStatements:
    def test_row_count(self):
        ingestor = _make(OnetTaskStatementsIngestor)
        rows = _fetch_sample(ingestor)
        assert len(rows) == 8


class TestFetchWorkActivities:
    def test_row_count(self):
        ingestor = _make(OnetWorkActivitiesIngestor)
        rows = _fetch_sample(ingestor)
        assert len(rows) == 10


class TestFetchWorkContext:
    def test_row_count(self):
        ingestor = _make(OnetWorkContextIngestor)
        rows = _fetch_sample(ingestor)
        assert len(rows) == 6

    def test_category_column_present(self):
        ingestor = _make(OnetWorkContextIngestor)
        rows = _fetch_sample(ingestor)
        assert "Category" in rows[0]


class TestFetchRelatedOccupations:
    def test_row_count(self):
        ingestor = _make(OnetRelatedOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        assert len(rows) == 24


# ============================================================
# Flatten Tests — Occupations
# ============================================================


class TestFlattenOccupations:
    def test_returns_list_of_dicts(self):
        ingestor = _make(OnetOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        assert isinstance(flat, list)
        assert len(flat) == 5
        assert isinstance(flat[0], dict)

    def test_soc_code_format_preserved(self):
        ingestor = _make(OnetOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        for record in flat:
            soc = record["onet_soc_code"]
            assert isinstance(soc, str)
            assert "." in soc
            parts = soc.split("-")
            assert len(parts) == 2
            assert "." in parts[1]

    def test_output_keys(self):
        ingestor = _make(OnetOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        expected = {"onet_soc_code", "title", "description"}
        for record in flat:
            assert set(record.keys()) == expected

    def test_no_metadata_fields(self):
        ingestor = _make(OnetOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        metadata = {"ingested_at", "source_url", "source_method", "load_date"}
        for record in flat:
            assert metadata.isdisjoint(set(record.keys()))

    def test_skips_null_grain(self):
        ingestor = _make(OnetOccupationsIngestor)
        raw = [
            {"O*NET-SOC Code": "", "Title": "Empty", "Description": "Nothing"},
            {"O*NET-SOC Code": "15-1252.00", "Title": "Software Dev", "Description": "Develop."},
        ]
        flat = ingestor.flatten(raw, "test")
        assert len(flat) == 1
        assert flat[0]["onet_soc_code"] == "15-1252.00"


# ============================================================
# Flatten Tests — Task Statements
# ============================================================


class TestFlattenTaskStatements:
    def test_row_count(self):
        ingestor = _make(OnetTaskStatementsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        assert len(flat) == 8

    def test_task_id_is_int(self):
        ingestor = _make(OnetTaskStatementsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        for record in flat:
            assert isinstance(record["task_id"], int)

    def test_task_type_preserved(self):
        ingestor = _make(OnetTaskStatementsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        types = {r["task_type"] for r in flat if r["task_type"] is not None}
        assert "Core" in types

    def test_incumbents_responding_is_int(self):
        ingestor = _make(OnetTaskStatementsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        for record in flat:
            if record["incumbents_responding"] is not None:
                assert isinstance(record["incumbents_responding"], int)

    def test_domain_source_preserved(self):
        ingestor = _make(OnetTaskStatementsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        sources = {r["domain_source"] for r in flat if r["domain_source"] is not None}
        assert "Incumbent" in sources


# ============================================================
# Flatten Tests — Work Activities
# ============================================================


class TestFlattenWorkActivities:
    def test_row_count(self):
        ingestor = _make(OnetWorkActivitiesIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        assert len(flat) == 10

    def test_data_value_is_float(self):
        ingestor = _make(OnetWorkActivitiesIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        for record in flat:
            assert isinstance(record["data_value"], float)

    def test_recommend_suppress_preserved(self):
        ingestor = _make(OnetWorkActivitiesIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        values = {r["recommend_suppress"] for r in flat if r["recommend_suppress"] is not None}
        assert "N" in values
        assert "Y" in values

    def test_not_relevant_preserved(self):
        ingestor = _make(OnetWorkActivitiesIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        values = {r["not_relevant"] for r in flat if r["not_relevant"] is not None}
        assert "N" in values
        assert "n/a" in values

    def test_scale_id_preserved(self):
        ingestor = _make(OnetWorkActivitiesIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        scales = {r["scale_id"] for r in flat}
        assert "IM" in scales
        assert "LV" in scales

    def test_n_is_int(self):
        ingestor = _make(OnetWorkActivitiesIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        for record in flat:
            if record["n"] is not None:
                assert isinstance(record["n"], int)

    def test_ci_bounds_are_float(self):
        ingestor = _make(OnetWorkActivitiesIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        for record in flat:
            if record["lower_ci_bound"] is not None:
                assert isinstance(record["lower_ci_bound"], float)
            if record["upper_ci_bound"] is not None:
                assert isinstance(record["upper_ci_bound"], float)

    def test_no_category_field(self):
        ingestor = _make(OnetWorkActivitiesIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        for record in flat:
            assert "category" not in record


# ============================================================
# Flatten Tests — Work Context
# ============================================================


class TestFlattenWorkContext:
    def test_row_count(self):
        ingestor = _make(OnetWorkContextIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        assert len(flat) == 6

    def test_category_field_present(self):
        ingestor = _make(OnetWorkContextIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        assert all("category" in r for r in flat)

    def test_category_is_int_or_none(self):
        ingestor = _make(OnetWorkContextIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        has_int = False
        has_none = False
        for record in flat:
            cat = record["category"]
            if cat is not None:
                assert isinstance(cat, int)
                has_int = True
            else:
                has_none = True
        assert has_int, "Expected at least one row with a category value"
        assert has_none, "Expected at least one row with null category"

    def test_has_cx_and_cxp_scale_types(self):
        """Real Work Context data has CX and CXP scale types."""
        ingestor = _make(OnetWorkContextIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        scales = {r["scale_id"] for r in flat}
        assert "CX" in scales
        assert "CXP" in scales

    def test_not_relevant_always_na(self):
        """In production Work Context, not_relevant is always 'n/a'."""
        ingestor = _make(OnetWorkContextIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        for record in flat:
            assert record["not_relevant"] == "n/a"


# ============================================================
# Flatten Tests — Related Occupations
# ============================================================


class TestFlattenRelatedOccupations:
    def test_row_count(self):
        ingestor = _make(OnetRelatedOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        assert len(flat) == 24

    def test_is_primary_derived_from_tier(self):
        """is_primary derived from Relatedness Tier: Primary-* = True."""
        ingestor = _make(OnetRelatedOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        for record in flat:
            tier = record["relatedness_tier"]
            if tier and tier.startswith("Primary"):
                assert record["is_primary"] is True
            elif tier == "Supplemental":
                assert record["is_primary"] is False

    def test_has_both_primary_and_supplemental(self):
        ingestor = _make(OnetRelatedOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        primaries = [r for r in flat if r["is_primary"] is True]
        supplementals = [r for r in flat if r["is_primary"] is False]
        assert len(primaries) > 0
        assert len(supplementals) > 0

    def test_related_index_is_int(self):
        ingestor = _make(OnetRelatedOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        for record in flat:
            assert isinstance(record["related_index"], int)

    def test_is_primary_is_bool(self):
        ingestor = _make(OnetRelatedOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        for record in flat:
            assert isinstance(record["is_primary"], bool)

    def test_output_keys(self):
        ingestor = _make(OnetRelatedOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        expected = {"onet_soc_code", "related_onet_soc_code", "related_index",
                    "is_primary", "relatedness_tier"}
        for record in flat:
            assert set(record.keys()) == expected

    def test_relatedness_tier_preserved(self):
        ingestor = _make(OnetRelatedOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        tiers = {r["relatedness_tier"] for r in flat if r["relatedness_tier"] is not None}
        assert "Primary-Short" in tiers
        assert "Primary-Long" in tiers
        assert "Supplemental" in tiers

    def test_twenty_rows_for_first_occupation(self):
        ingestor = _make(OnetRelatedOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        first_soc = flat[0]["onet_soc_code"]
        first_rows = [r for r in flat if r["onet_soc_code"] == first_soc]
        assert len(first_rows) == 20
        primary_count = sum(1 for r in first_rows if r["is_primary"])
        supplemental_count = sum(1 for r in first_rows if not r["is_primary"])
        assert primary_count == 10
        assert supplemental_count == 10


# ============================================================
# Golden Dataset Tests — Real O*NET Values
# ============================================================


class TestGoldenDataset:
    """Verify specific data values from the real O*NET 30.2 database.

    These assertions use known values extracted from the actual source
    files, not fabricated data. If these fail, the ingestor is garbling
    column mappings or coercing values incorrectly.
    """

    def test_chief_executives_title(self):
        ingestor = _make(OnetOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        ceo = [r for r in flat if r["onet_soc_code"] == "11-1011.00"]
        assert len(ceo) == 1
        assert ceo[0]["title"] == "Chief Executives"

    def test_legislators_title(self):
        ingestor = _make(OnetOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        leg = [r for r in flat if r["onet_soc_code"] == "11-1031.00"]
        assert len(leg) == 1
        assert leg[0]["title"] == "Legislators"

    def test_ceo_task_id_8823(self):
        """Chief Executives task 8823: financial/budget activities."""
        ingestor = _make(OnetTaskStatementsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        task = [r for r in flat if r["task_id"] == 8823]
        assert len(task) == 1
        assert task[0]["onet_soc_code"] == "11-1011.00"
        assert "financial or budget activities" in task[0]["task"]
        assert task[0]["task_type"] == "Core"
        assert task[0]["incumbents_responding"] == 95

    def test_ceo_getting_information_im_rating(self):
        """Chief Executives: Getting Information IM = 4.56."""
        ingestor = _make(OnetWorkActivitiesIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        match = [r for r in flat
                 if r["onet_soc_code"] == "11-1011.00"
                 and r["element_id"] == "4.A.1.a.1"
                 and r["scale_id"] == "IM"]
        assert len(match) == 1
        assert match[0]["data_value"] == 4.56
        assert match[0]["element_name"] == "Getting Information"
        assert match[0]["n"] == 29

    def test_software_dev_getting_information_im_rating(self):
        """Software Developers: Getting Information IM = 4.04."""
        ingestor = _make(OnetWorkActivitiesIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        match = [r for r in flat
                 if r["onet_soc_code"] == "15-1252.00"
                 and r["element_id"] == "4.A.1.a.1"
                 and r["scale_id"] == "IM"]
        assert len(match) == 1
        assert match[0]["data_value"] == 4.04

    def test_ceo_public_speaking_cx_rating(self):
        """Chief Executives: Public Speaking CX = 3.07."""
        ingestor = _make(OnetWorkContextIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        match = [r for r in flat
                 if r["onet_soc_code"] == "11-1011.00"
                 and r["element_id"] == "4.C.1.a.2.c"
                 and r["scale_id"] == "CX"]
        assert len(match) == 1
        assert match[0]["data_value"] == 3.07
        assert match[0]["element_name"] == "Public Speaking"
        assert match[0]["category"] is None  # CX rows have n/a category

    def test_cxp_categories_sum_to_100(self):
        """CXP percentage categories for one element should sum to ~100%."""
        ingestor = _make(OnetWorkContextIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        cxp = [r for r in flat
               if r["scale_id"] == "CXP"
               and r["onet_soc_code"] == "11-1011.00"
               and r["element_id"] == "4.C.1.a.2.c"]
        assert len(cxp) == 5  # 5 response categories
        total = sum(r["data_value"] for r in cxp)
        assert abs(total - 100.0) < 1.0, f"CXP categories sum to {total}, expected ~100"

    def test_ceo_first_related_occupation(self):
        """Chief Executives: first related occupation is General and Ops Managers."""
        ingestor = _make(OnetRelatedOccupationsIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        match = [r for r in flat
                 if r["onet_soc_code"] == "11-1011.00"
                 and r["related_index"] == 1]
        assert len(match) == 1
        assert match[0]["related_onet_soc_code"] == "11-1021.00"
        assert match[0]["is_primary"] is True
        assert match[0]["relatedness_tier"] == "Primary-Short"

    def test_suppressed_activity_has_y_flag(self):
        """Repairing Mechanical Equipment for CEO has recommend_suppress=Y."""
        ingestor = _make(OnetWorkActivitiesIngestor)
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "onet")
        match = [r for r in flat
                 if r["onet_soc_code"] == "11-1011.00"
                 and r["element_id"] == "4.A.3.b.4"
                 and r["recommend_suppress"] == "Y"]
        assert len(match) > 0


# ============================================================
# Coercion Edge Cases
# ============================================================


class TestCoercionEdgeCases:
    def test_coerce_string_none(self):
        assert OnetBaseIngestor._coerce_string(None) is None

    def test_coerce_string_empty(self):
        assert OnetBaseIngestor._coerce_string("") is None

    def test_coerce_string_whitespace(self):
        assert OnetBaseIngestor._coerce_string("  ") is None

    def test_coerce_string_strips(self):
        assert OnetBaseIngestor._coerce_string("  hello  ") == "hello"

    def test_coerce_onet_soc_preserves_format(self):
        assert OnetBaseIngestor._coerce_onet_soc("15-1252.00") == "15-1252.00"

    def test_coerce_onet_soc_none(self):
        assert OnetBaseIngestor._coerce_onet_soc(None) is None

    def test_coerce_onet_soc_empty(self):
        assert OnetBaseIngestor._coerce_onet_soc("") is None

    def test_coerce_double_valid(self):
        assert OnetBaseIngestor._coerce_double("4.62") == 4.62

    def test_coerce_double_none(self):
        assert OnetBaseIngestor._coerce_double(None) is None

    def test_coerce_double_empty(self):
        assert OnetBaseIngestor._coerce_double("") is None

    def test_coerce_double_na(self):
        assert OnetBaseIngestor._coerce_double("n/a") is None

    def test_coerce_double_preserves_precision(self):
        assert OnetBaseIngestor._coerce_double("4.626789") == 4.626789

    def test_coerce_int_valid(self):
        assert OnetBaseIngestor._coerce_int("25") == 25

    def test_coerce_int_from_float_string(self):
        assert OnetBaseIngestor._coerce_int("25.0") == 25

    def test_coerce_int_none(self):
        assert OnetBaseIngestor._coerce_int(None) is None

    def test_coerce_int_empty(self):
        assert OnetBaseIngestor._coerce_int("") is None

    def test_coerce_int_invalid(self):
        assert OnetBaseIngestor._coerce_int("abc") is None

    def test_coerce_long_valid(self):
        assert OnetBaseIngestor._coerce_long("12345") == 12345

    def test_coerce_long_none(self):
        assert OnetBaseIngestor._coerce_long(None) is None
