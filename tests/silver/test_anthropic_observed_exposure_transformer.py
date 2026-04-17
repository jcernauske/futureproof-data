"""Smoke tests for AnthropicObservedExposureTransformer.

Minimal stubs — @test-writer will expand. For now:
  - schema sanity
  - transform_rows produces one row per SOC
  - broad-code expansion fans out via the BLS prefix map
  - soc_match flag is set correctly
"""

from __future__ import annotations

import datetime

import pytest

from silver.anthropic_observed_exposure_transformer import (
    AnthropicObservedExposureTransformer,
    GRAIN_FIELDS,
    GRAIN_PREFIX,
    SPEC_NAME,
    _aggregate_observed_exposure,
    _normalize_soc_code,
    _weighted_average,
    get_silver_schema,
    transform_rows,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bls_rows() -> list[dict]:
    """Minimal BLS OOH stub with detailed + broad codes."""
    return [
        {"soc_code": "15-1252", "occupation_title": "Software Developers"},
        {"soc_code": "13-2051", "occupation_title": "Financial Analysts"},
        {"soc_code": "29-1141", "occupation_title": "Registered Nurses"},
        {"soc_code": "25-2021", "occupation_title": "Elementary Teachers"},
        {"soc_code": "51-3011", "occupation_title": "Bakers"},  # detailed
        # Note: 51-3010 (broad) intentionally not in BLS to exercise expansion
    ]


@pytest.fixture
def bronze_rows() -> list[dict]:
    """Handful of task-level rows covering detailed, broad, and null SOC."""
    return [
        {
            "task_id": "1001",
            "task_statement": "write programs.",
            "soc_code": "15-1252",
            "soc_title": "Software Developers",
            "task_pct": 3.5,
            "automation_pct": 45.0,
            "augmentation_pct": 50.0,
            "source_release": "release_2025_03_27",
        },
        {
            "task_id": "1002",
            "task_statement": "debug code.",
            "soc_code": "15-1252",
            "soc_title": "Software Developers",
            "task_pct": 2.8,
            "automation_pct": 42.0,
            "augmentation_pct": 53.0,
            "source_release": "release_2025_03_27",
        },
        {
            "task_id": "2001",
            "task_statement": "analyze financials.",
            "soc_code": "13-2051",
            "soc_title": "Financial Analysts",
            "task_pct": 2.1,
            "automation_pct": 50.0,
            "augmentation_pct": 45.0,
            "source_release": "release_2025_03_27",
        },
        {
            "task_id": "10001",
            "task_statement": "bake bread.",
            "soc_code": "51-3010",  # broad — should expand to 51-3011
            "soc_title": "Bakers",
            "task_pct": 0.4,
            "automation_pct": 10.0,
            "augmentation_pct": 5.0,
            "source_release": "release_2025_03_27",
        },
        {
            "task_id": "orphan",
            "task_statement": "orphan task.",
            "soc_code": None,  # null SOC — should be skipped
            "soc_title": None,
            "task_pct": 100.0,
            "automation_pct": None,
            "augmentation_pct": None,
            "source_release": "release_2025_03_27",
        },
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSchema:
    """Schema sanity checks."""

    def test_schema_is_iceberg_schema(self) -> None:
        from pyiceberg.schema import Schema

        assert isinstance(get_silver_schema(), Schema)

    def test_schema_has_expected_fields(self) -> None:
        schema = get_silver_schema()
        names = {f.name for f in schema.fields}
        expected = {
            "record_id", "soc_code", "soc_title", "observed_exposure_pct",
            "automation_pct", "augmentation_pct", "task_count", "soc_match",
            "source_release", "promoted_at",
        }
        assert expected.issubset(names)

    def test_grain_constants(self) -> None:
        assert GRAIN_FIELDS == ["soc_code"]
        assert GRAIN_PREFIX == "aoe"
        assert SPEC_NAME == "silver-base-anthropic-observed-exposure"


class TestNormalization:
    """SOC code normalization helpers."""

    def test_normalize_strips_onet_overlay(self) -> None:
        assert _normalize_soc_code("11-1011.00") == "11-1011"

    def test_normalize_passes_through_valid(self) -> None:
        assert _normalize_soc_code("15-1252") == "15-1252"

    def test_normalize_rejects_invalid(self) -> None:
        assert _normalize_soc_code("abc") is None
        assert _normalize_soc_code("") is None
        assert _normalize_soc_code(None) is None


class TestAggregation:
    """Pure aggregation helpers."""

    def test_observed_exposure_sum(self) -> None:
        assert _aggregate_observed_exposure([1.0, 2.0, 3.0]) == 6.0

    def test_observed_exposure_all_none(self) -> None:
        assert _aggregate_observed_exposure([None, None]) == 0.0

    def test_observed_exposure_clamped_at_100(self) -> None:
        assert _aggregate_observed_exposure([60.0, 60.0]) == 100.0

    def test_weighted_average_basic(self) -> None:
        assert _weighted_average([10.0, 20.0], [1.0, 3.0]) == pytest.approx(17.5)

    def test_weighted_average_empty(self) -> None:
        assert _weighted_average([], []) is None

    def test_weighted_average_zero_weights_falls_back_to_mean(self) -> None:
        assert _weighted_average([10.0, 20.0], [0.0, 0.0]) == pytest.approx(15.0)


class TestTransformRows:
    """End-to-end transform_rows smoke."""

    def test_produces_one_row_per_soc(self, bronze_rows, bls_rows) -> None:
        rows = transform_rows(bronze_rows, bls_rows)
        soc_codes = [r["soc_code"] for r in rows]
        assert len(soc_codes) == len(set(soc_codes))
        # Detailed codes should appear
        assert "15-1252" in soc_codes
        assert "13-2051" in soc_codes
        # Broad code 51-3010 should expand to detailed 51-3011
        assert "51-3011" in soc_codes
        assert "51-3010" not in soc_codes

    def test_null_soc_rows_skipped(self, bronze_rows, bls_rows) -> None:
        rows = transform_rows(bronze_rows, bls_rows)
        for row in rows:
            assert row["soc_code"] is not None

    def test_soc_match_reflects_bls_membership(self, bronze_rows, bls_rows) -> None:
        rows = transform_rows(bronze_rows, bls_rows)
        by_soc = {r["soc_code"]: r for r in rows}
        assert by_soc["15-1252"]["soc_match"] is True
        assert by_soc["51-3011"]["soc_match"] is True

    def test_task_count_is_aggregated(self, bronze_rows, bls_rows) -> None:
        rows = transform_rows(bronze_rows, bls_rows)
        by_soc = {r["soc_code"]: r for r in rows}
        # 15-1252 has two tasks in the fixture
        assert by_soc["15-1252"]["task_count"] == 2

    def test_record_id_is_deterministic(self, bronze_rows, bls_rows) -> None:
        ts = datetime.datetime(2026, 4, 16, tzinfo=datetime.timezone.utc)
        rows1 = transform_rows(bronze_rows, bls_rows, promoted_at=ts)
        rows2 = transform_rows(bronze_rows, bls_rows, promoted_at=ts)
        ids1 = [r["record_id"] for r in rows1]
        ids2 = [r["record_id"] for r in rows2]
        assert ids1 == ids2


class TestTransformerClass:
    """Smoke test: the OO wrapper instantiates and proxies."""

    def test_instantiates(self, tmp_path) -> None:
        t = AnthropicObservedExposureTransformer(project_dir=tmp_path)
        assert t.project_dir == tmp_path.resolve()

    def test_get_schema_matches_module_function(self, tmp_path) -> None:
        t = AnthropicObservedExposureTransformer(project_dir=tmp_path)
        # Both return equivalent schemas
        a = t.get_schema()
        b = get_silver_schema()
        assert [f.name for f in a.fields] == [f.name for f in b.fields]


class TestSumAggregation:
    """observed_exposure_pct is the SUM of per-(task,soc) Bronze values.

    Covers Bug 1/2 regression: if Bronze emits one row per (task, SOC)
    pair with pre-split pct values, Silver must SUM them (not mean or
    weighted-mean) to reconstruct the per-SOC share of global Claude
    traffic.
    """

    def test_observed_exposure_is_sum_of_task_pcts(self, bls_rows) -> None:
        """Two Software Developer tasks at 3.5 + 2.8 => observed exposure 6.3."""
        bronze = [
            {
                "task_id": "1001",
                "task_statement": "write programs.",
                "soc_code": "15-1252",
                "soc_title": "Software Developers",
                "task_pct": 3.5,
                "automation_pct": 40.0,
                "augmentation_pct": 55.0,
                "source_release": "release_2025_03_27",
            },
            {
                "task_id": "1002",
                "task_statement": "debug code.",
                "soc_code": "15-1252",
                "soc_title": "Software Developers",
                "task_pct": 2.8,
                "automation_pct": 42.0,
                "augmentation_pct": 53.0,
                "source_release": "release_2025_03_27",
            },
        ]
        rows = transform_rows(bronze, bls_rows)
        by_soc = {r["soc_code"]: r for r in rows}
        assert by_soc["15-1252"]["observed_exposure_pct"] == pytest.approx(6.3)

    def test_none_placeholder_excluded_from_aggregation(self, bls_rows) -> None:
        """The ``task_name='none'`` placeholder has null SOC => excluded."""
        bronze = [
            {
                "task_id": "1001",
                "task_statement": "write programs.",
                "soc_code": "15-1252",
                "soc_title": "Software Developers",
                "task_pct": 3.5,
                "automation_pct": 40.0,
                "augmentation_pct": 55.0,
                "source_release": "release_2025_03_27",
            },
            # Null-SOC placeholder row (Bronze keeps it; Silver must drop)
            {
                "task_id": "none",
                "task_statement": "none",
                "soc_code": None,
                "soc_title": None,
                "task_pct": 38.75,
                "automation_pct": 30.0,
                "augmentation_pct": 65.0,
                "source_release": "release_2025_03_27",
            },
        ]
        rows = transform_rows(bronze, bls_rows)
        soc_codes = [r["soc_code"] for r in rows]
        # Only the Software Developer SOC should appear
        assert soc_codes == ["15-1252"]
        # The 38.75 from the 'none' row must NOT leak into any SOC total
        assert rows[0]["observed_exposure_pct"] == pytest.approx(3.5)

    def test_multi_soc_fanout_split_values_preserve_task_weight(self, bls_rows) -> None:
        """Two Bronze rows from a 2-SOC fan-out each at pct/2 => SOC total = pct/2.

        After Bronze splits a 2.0% task across 2 SOCs, each SOC sees 1.0
        for that task — NOT the full 2.0. Verifies Silver does not double
        count the original task weight.
        """
        bronze = [
            # Same task text, same raw pct=2.0, split into 1.0 per SOC
            {
                "task_id": "11001",
                "task_statement": "write documentation.",
                "soc_code": "15-1252",
                "soc_title": "Software Developers",
                "task_pct": 1.0,  # 2.0 / 2
                "automation_pct": 40.0,
                "augmentation_pct": 55.0,
                "source_release": "release_2025_03_27",
            },
            # Technical Writers is not in bls_rows fixture → soc_match=false
            # but the row still aggregates.
            {
                "task_id": "11002",
                "task_statement": "write documentation.",
                "soc_code": "27-3042",
                "soc_title": "Technical Writers",
                "task_pct": 1.0,
                "automation_pct": 40.0,
                "augmentation_pct": 55.0,
                "source_release": "release_2025_03_27",
            },
        ]
        rows = transform_rows(bronze, bls_rows)
        by_soc = {r["soc_code"]: r for r in rows}
        assert by_soc["15-1252"]["observed_exposure_pct"] == pytest.approx(1.0)
        assert by_soc["27-3042"]["observed_exposure_pct"] == pytest.approx(1.0)
        # Sum across all SOCs reconstructs the pre-split task total
        total = sum(r["observed_exposure_pct"] for r in rows)
        assert total == pytest.approx(2.0)
