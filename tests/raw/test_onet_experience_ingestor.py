"""Tests for OnetExperienceIngestor.

Covers the 8th O*NET subclass that ingests
``Education, Training, and Experience.txt`` into ``raw.onet_experience``.

Fixture: ``tests/raw/onet_samples/Education, Training, and Experience.txt``
contains a representative slice of O*NET 30.2 data across all four scales
(RL, RW, PT, OJ), plus deliberately-crafted edge cases for
``recommend_suppress='Y'``, null CI bounds, and a single-category
100% distribution.

These tests use only the local cache path, never the network.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    TimestampType,
)

from raw.onet_ingestor import OnetBaseIngestor, OnetExperienceIngestor

SAMPLES_DIR = Path(__file__).parent / "onet_samples"

# Regex matching the O*NET-SOC 8.0 code format ``XX-XXXX.XX``.
ONET_SOC_RE = re.compile(r"^\d{2}-\d{4}\.\d{2}$")


def _make(cls: type) -> OnetExperienceIngestor:
    """Create an ingestor instance without requiring real config objects."""
    obj = cls.__new__(cls)
    return obj  # type: ignore[return-value]


def _fetch_sample(ingestor: OnetExperienceIngestor) -> list[dict]:
    """Run fetch() with the local sample cache dir and return the raw rows."""
    entities = {"onet": "O*NET Test"}
    result = ingestor.fetch(entities, "bulk_zip_download", cache_dir=str(SAMPLES_DIR))
    return result["onet"]


# ============================================================
# Constants & Registration
# ============================================================


class TestConstants:
    def test_is_subclass_of_base(self) -> None:
        assert issubclass(OnetExperienceIngestor, OnetBaseIngestor)

    def test_source_filename(self) -> None:
        assert (
            OnetExperienceIngestor.SOURCE_FILENAME
            == "Education, Training, and Experience.txt"
        )

    def test_inherits_download_url(self) -> None:
        assert "onetcenter.org" in OnetExperienceIngestor.DOWNLOAD_URL
        assert OnetExperienceIngestor.DOWNLOAD_URL.endswith(".zip")

    def test_inherits_cache_dir(self) -> None:
        assert OnetExperienceIngestor.CACHE_DIR == "data/raw/onet_cache"

    def test_module_docstring_lists_experience(self) -> None:
        """The module docstring should mention Experience as one of the six subclasses."""
        import raw.onet_ingestor as mod

        assert mod.__doc__ is not None
        assert "Six thin subclasses" in mod.__doc__
        assert "Experience" in mod.__doc__


# ============================================================
# Schema Tests
# ============================================================


class TestExperienceSchema:
    def test_returns_iceberg_schema(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        assert isinstance(ingestor.get_schema(), Schema)

    def test_field_count(self) -> None:
        """13 data fields + 4 metadata = 17."""
        ingestor = _make(OnetExperienceIngestor)
        assert len(ingestor.get_schema().fields) == 17

    def test_has_grain_fields(self) -> None:
        """Grain = (onet_soc_code, element_id, scale_id, category)."""
        ingestor = _make(OnetExperienceIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        for grain in ("onet_soc_code", "element_id", "scale_id", "category"):
            assert grain in names, f"grain field {grain!r} missing from schema"

    def test_has_percent_frequency_field(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        assert "data_value" in names

    def test_has_recommend_suppress(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        assert "recommend_suppress" in names

    def test_has_metadata_fields(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        for meta in ("ingested_at", "source_url", "source_method", "load_date"):
            assert meta in names

    def test_has_no_not_relevant_column(self) -> None:
        """Education, Training, and Experience.txt has no Not Relevant column."""
        ingestor = _make(OnetExperienceIngestor)
        names = [f.name for f in ingestor.get_schema().fields]
        assert "not_relevant" not in names

    def test_required_field_flags(self) -> None:
        """Required == spec: onet_soc_code, element_id, element_name, scale_id,
        category, data_value + 4 metadata fields. n and CIs are nullable."""
        ingestor = _make(OnetExperienceIngestor)
        required = {f.name for f in ingestor.get_schema().fields if f.required}
        expected_required = {
            "onet_soc_code",
            "element_id",
            "element_name",
            "scale_id",
            "category",
            "data_value",
            "ingested_at",
            "source_url",
            "source_method",
            "load_date",
        }
        assert required == expected_required

    def test_optional_fields(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        optional = {f.name for f in ingestor.get_schema().fields if not f.required}
        expected_optional = {
            "n",
            "standard_error",
            "lower_ci_bound",
            "upper_ci_bound",
            "recommend_suppress",
            "date",
            "domain_source",
        }
        assert optional == expected_optional

    def test_field_types(self) -> None:
        """Spot-check column types match the Bronze schema."""
        ingestor = _make(OnetExperienceIngestor)
        types = {f.name: type(f.field_type) for f in ingestor.get_schema().fields}
        assert types["onet_soc_code"] is StringType
        assert types["element_id"] is StringType
        assert types["scale_id"] is StringType
        assert types["category"] is IntegerType
        assert types["data_value"] is DoubleType
        assert types["n"] is IntegerType
        assert types["standard_error"] is DoubleType
        assert types["lower_ci_bound"] is DoubleType
        assert types["upper_ci_bound"] is DoubleType
        assert types["recommend_suppress"] is StringType
        assert types["ingested_at"] is TimestampType
        assert types["load_date"] is DateType


# ============================================================
# Fetch Tests
# ============================================================


class TestFetch:
    def test_returns_dict(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        result = ingestor.fetch({"onet": "test"}, "test", cache_dir=str(SAMPLES_DIR))
        assert isinstance(result, dict)
        assert "onet" in result

    def test_returns_parsed_rows(self) -> None:
        """Fixture file has 27 data rows (including one with null data_value)."""
        ingestor = _make(OnetExperienceIngestor)
        rows = _fetch_sample(ingestor)
        assert isinstance(rows, list)
        assert len(rows) == 27
        assert all(isinstance(r, dict) for r in rows)

    def test_tab_delimited_parse_preserves_columns(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        rows = _fetch_sample(ingestor)
        expected_cols = {
            "O*NET-SOC Code",
            "Element ID",
            "Element Name",
            "Scale ID",
            "Category",
            "Data Value",
            "N",
            "Standard Error",
            "Lower CI Bound",
            "Upper CI Bound",
            "Recommend Suppress",
            "Date",
            "Domain Source",
        }
        assert expected_cols.issubset(rows[0].keys())

    def test_soc_code_preserved_as_string_in_raw(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        rows = _fetch_sample(ingestor)
        for row in rows:
            soc = row["O*NET-SOC Code"]
            assert isinstance(soc, str)
            assert "." in soc  # O*NET-SOC is XX-XXXX.XX, never a float


# ============================================================
# Flatten Tests
# ============================================================


class TestFlatten:
    def test_returns_list_of_dicts(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        assert isinstance(flat, list)
        assert all(isinstance(r, dict) for r in flat)

    def test_skips_rows_with_null_data_value(self) -> None:
        """Fixture line 26 is a suppressed row with blank data_value → skipped."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        assert len(flat) == 26  # 27 raw rows minus 1 with null data_value

    def test_all_four_scales_preserved(self) -> None:
        """Bronze must keep RL, RW, PT, OJ — Silver filters to RW."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        scales = {r["scale_id"] for r in flat}
        assert scales == {"RL", "RW", "PT", "OJ"}

    def test_scale_row_counts_match_fixture(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        from collections import Counter

        counts = Counter(r["scale_id"] for r in flat)
        # RL: 4 CEO rows. PT: 3 CEO rows. OJ: 3 CEO rows.
        # RW: 6 CEO + 5 SW dev + 3 Retail + 1 suppressed single-cat + 1 single-cat-100% = 16
        assert counts["RL"] == 4
        assert counts["PT"] == 3
        assert counts["OJ"] == 3
        assert counts["RW"] == 16

    def test_soc_code_format_is_string_not_float(self) -> None:
        """onet_soc_code must be a string in XX-XXXX.XX format — never cast to float."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        for r in flat:
            soc = r["onet_soc_code"]
            assert isinstance(soc, str)
            assert ONET_SOC_RE.match(soc), f"onet_soc_code {soc!r} not in XX-XXXX.XX format"

    def test_category_is_int(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        for r in flat:
            assert isinstance(r["category"], int)

    def test_data_value_is_float(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        for r in flat:
            assert isinstance(r["data_value"], float)

    def test_data_value_range_is_percent(self) -> None:
        """data_value is a percent frequency: 0.0 <= v <= 100.0."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        for r in flat:
            assert 0.0 <= r["data_value"] <= 100.0

    def test_output_keys(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        expected = {
            "onet_soc_code",
            "element_id",
            "element_name",
            "scale_id",
            "category",
            "data_value",
            "n",
            "standard_error",
            "lower_ci_bound",
            "upper_ci_bound",
            "recommend_suppress",
            "date",
            "domain_source",
        }
        for record in flat:
            assert set(record.keys()) == expected

    def test_no_metadata_fields_at_flatten_time(self) -> None:
        """Framework adds metadata; flatten() must not."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        metadata = {"ingested_at", "source_url", "source_method", "load_date"}
        for record in flat:
            assert metadata.isdisjoint(record.keys())

    def test_recommend_suppress_preserved_verbatim(self) -> None:
        """Must keep 'Y'/'N' strings verbatim for downstream DQ."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        values = {r["recommend_suppress"] for r in flat if r["recommend_suppress"] is not None}
        assert "N" in values
        assert "Y" in values
        # and no surprise coercion (no bools, no "y"/"n" lowercased)
        for v in values:
            assert v in ("Y", "N")

    def test_suppressed_row_retained_when_data_value_present(self) -> None:
        """Single-category 100% row with recommend_suppress='Y' (soc 29-1069.01)
        must still land in Bronze — DQ flags it, Silver decides how to use it."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        suppressed = [
            r
            for r in flat
            if r["onet_soc_code"] == "29-1069.01" and r["recommend_suppress"] == "Y"
        ]
        assert len(suppressed) == 1
        assert suppressed[0]["scale_id"] == "RW"
        assert suppressed[0]["category"] == 7
        assert suppressed[0]["data_value"] == 100.0

    def test_null_ci_bounds_coerced_to_none(self) -> None:
        """Rows with empty CI bound cells must produce None, not '' or 0.0."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        matches = [r for r in flat if r["onet_soc_code"] == "49-9071.00"]
        assert len(matches) == 1
        row = matches[0]
        assert row["lower_ci_bound"] is None
        assert row["upper_ci_bound"] is None
        # But standard_error is present
        assert row["standard_error"] == 0.0

    def test_n_is_int_or_none(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        for r in flat:
            assert r["n"] is None or isinstance(r["n"], int)

    def test_ci_bounds_are_float_or_none(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        for r in flat:
            for bound in ("lower_ci_bound", "upper_ci_bound"):
                v = r[bound]
                assert v is None or isinstance(v, float)

    def test_element_id_for_rw_is_3_a_1(self) -> None:
        """All RW rows must carry element_id 3.A.1 (Related Work Experience)."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        rw_rows = [r for r in flat if r["scale_id"] == "RW"]
        assert len(rw_rows) > 0
        for r in rw_rows:
            assert r["element_id"] == "3.A.1"
            assert r["element_name"] == "Related Work Experience"

    def test_element_id_for_rl_is_2_d_1(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        rl_rows = [r for r in flat if r["scale_id"] == "RL"]
        assert len(rl_rows) > 0
        for r in rl_rows:
            assert r["element_id"] == "2.D.1"

    def test_domain_source_preserved(self) -> None:
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        sources = {r["domain_source"] for r in flat if r["domain_source"] is not None}
        assert sources == {"Incumbent"}

    def test_skips_rows_with_null_required_fields(self) -> None:
        """Rows missing grain or core required fields are skipped, not written as nulls."""
        ingestor = _make(OnetExperienceIngestor)
        raw = [
            # Missing data_value → skip
            {
                "O*NET-SOC Code": "11-1011.00",
                "Element ID": "3.A.1",
                "Element Name": "Related Work Experience",
                "Scale ID": "RW",
                "Category": "1",
                "Data Value": "",
                "Recommend Suppress": "N",
            },
            # Missing onet_soc_code → skip
            {
                "O*NET-SOC Code": "",
                "Element ID": "3.A.1",
                "Element Name": "Related Work Experience",
                "Scale ID": "RW",
                "Category": "1",
                "Data Value": "50.0",
                "Recommend Suppress": "N",
            },
            # Valid row
            {
                "O*NET-SOC Code": "15-1252.00",
                "Element ID": "3.A.1",
                "Element Name": "Related Work Experience",
                "Scale ID": "RW",
                "Category": "7",
                "Data Value": "45.33",
                "Recommend Suppress": "N",
            },
        ]
        flat = ingestor.flatten(raw, "test")
        assert len(flat) == 1
        assert flat[0]["onet_soc_code"] == "15-1252.00"


# ============================================================
# Deduplication / Grain
# ============================================================


class TestGrainAndDedup:
    def test_flatten_output_is_unique_on_grain(self) -> None:
        """Output rows must be unique on (onet_soc_code, element_id, scale_id, category).

        Dedup at the grain is enforced at Iceberg-append time by the framework,
        but the fixture-derived flatten output should already be unique.
        """
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        keys = [
            (r["onet_soc_code"], r["element_id"], r["scale_id"], r["category"])
            for r in flat
        ]
        assert len(keys) == len(set(keys)), "duplicate grain keys in flatten output"

    def test_grain_key_covers_all_scales_for_one_occupation(self) -> None:
        """For CEO (11-1011.00) the fixture carries rows across all four scales."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        ceo_scales = {r["scale_id"] for r in flat if r["onet_soc_code"] == "11-1011.00"}
        assert ceo_scales == {"RL", "RW", "PT", "OJ"}


# ============================================================
# Golden Dataset — Real O*NET Values
# ============================================================


class TestGoldenDataset:
    """Assert specific values that the Silver transformer will depend on.

    These encode the expected weighted-median and spot-check behavior called
    out in the spec test matrix (11-1011 senior, 41-2031 entry, multi-detail
    aggregation, single-category 100%, all-suppressed).
    """

    def test_ceo_rw_distribution_skews_senior(self) -> None:
        """11-1011 (Chief Executives) should have RW weight concentrated at cat >= 9."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        rw = [
            r
            for r in flat
            if r["onet_soc_code"] == "11-1011.00" and r["scale_id"] == "RW"
        ]
        high_exp_weight = sum(r["data_value"] for r in rw if r["category"] >= 9)
        assert high_exp_weight > 50.0  # most CEOs need >= 6 years experience

    def test_retail_rw_distribution_skews_entry(self) -> None:
        """41-2031 (Retail Salespersons) should have RW weight concentrated at cat 1."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        rw = [
            r
            for r in flat
            if r["onet_soc_code"] == "41-2031.00" and r["scale_id"] == "RW"
        ]
        cat1 = next(r for r in rw if r["category"] == 1)
        assert cat1["data_value"] > 50.0  # majority "None" for retail

    def test_rw_percentages_sum_roughly_to_100_per_occupation(self) -> None:
        """Sanity check: percent-frequency RW distributions sum to ~100% per SOC."""
        ingestor = _make(OnetExperienceIngestor)
        flat = ingestor.flatten(_fetch_sample(ingestor), "onet")
        by_soc: dict[str, float] = {}
        for r in flat:
            if r["scale_id"] != "RW":
                continue
            by_soc.setdefault(r["onet_soc_code"], 0.0)
            by_soc[r["onet_soc_code"]] += r["data_value"]
        # CEO, SW dev, retail: ~100. Suppressed 29-1069.01 has only 1 kept row (100).
        # 49-9071 has single-cat 100.
        for soc, total in by_soc.items():
            assert 99.0 <= total <= 101.0, (
                f"{soc}: RW rows sum to {total}, expected ~100"
            )


# ============================================================
# Coercion Edge Cases Specific to Experience Data
# ============================================================


class TestCoercionEdgeCases:
    def test_empty_string_category_coerced_to_none(self) -> None:
        assert OnetBaseIngestor._coerce_int("") is None

    def test_whitespace_data_value_coerced_to_none(self) -> None:
        assert OnetBaseIngestor._coerce_double("   ") is None

    def test_recommend_suppress_preserved_as_string(self) -> None:
        """Y/N must NOT be coerced to bool."""
        assert OnetBaseIngestor._coerce_string("Y") == "Y"
        assert OnetBaseIngestor._coerce_string("N") == "N"

    def test_onet_soc_format_preserved(self) -> None:
        """Multi-detail codes (XX-XXXX.01) preserved as string, not cast to float."""
        assert OnetBaseIngestor._coerce_onet_soc("29-1069.01") == "29-1069.01"
        assert OnetBaseIngestor._coerce_onet_soc("15-1252.00") == "15-1252.00"


# ============================================================
# Registration in the rebuild-all runner
# ============================================================


class TestRegistration:
    def test_registered_in_rebuild_all(self) -> None:
        """scripts/rebuild_all.py must list OnetExperienceIngestor alongside siblings."""
        path = (
            Path(__file__).resolve().parents[2]
            / "scripts"
            / "rebuild_all.py"
        )
        source = path.read_text()
        assert "OnetExperienceIngestor" in source, (
            "OnetExperienceIngestor must be imported + registered in scripts/rebuild_all.py"
        )
        assert "onet_experience" in source, (
            "table name 'onet_experience' must be registered in the O*NET runner loop"
        )


# ============================================================
# Re-exportability (sanity on public API)
# ============================================================


def test_ingestor_is_public_from_module() -> None:
    """Smoke test: the new class is importable at the module's public entry point."""
    from raw import onet_ingestor as mod

    assert hasattr(mod, "OnetExperienceIngestor")
    assert issubclass(mod.OnetExperienceIngestor, mod.OnetBaseIngestor)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
