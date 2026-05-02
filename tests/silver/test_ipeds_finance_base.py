"""Tests for the Silver/base zone IPEDS Finance transformer.

Covers:
  - derive_per_fte: NULL cascades + zero/negative-FTE guard + arithmetic invariant
  - derive_marketing_ratio: NULLIF(instruction, 0) semantics + zero-instruction case
  - _to_optional_float: NaN rejection + None/float pass-through
  - transform_row: missing-required-field ValueError paths + record_id determinism
  - transform_rows: duplicate-UNITID rejection + same-length output
  - Stanford golden-row fixture (UNITID 243744 → ipf-267f20f48b4b772f)
  - F3-row NULL-endowment cascade through endowment_per_fte
  - Schema (15 fields, dense IDs, exact column names)
  - Integration: bronze → base end-to-end via promote_ipeds_finance_base

Per the staff-engineer canonical test list (governance/approvals/
full-pipeline-ipeds-finance-staff-review.md): 15 base assertions minimum.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    NestedField,
    StringType,
    TimestampType,
)

from silver.ipeds_finance_base import (
    BASE_NAMESPACE,
    BASE_TABLE_NAME,
    GRAIN_FIELDS,
    GRAIN_PREFIX,
    SPEC_NAME,
    _to_optional_float,
    derive_marketing_ratio,
    derive_per_fte,
    get_base_schema,
    promote_ipeds_finance_base,
    transform_row,
    transform_rows,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


LOAD_DATE = datetime.date(2026, 4, 30)
INGESTED_AT = datetime.datetime(2026, 4, 30, 12, 0, 0, tzinfo=datetime.timezone.utc)


def _stanford_bronze_row() -> dict:
    """Stanford UNITID 243744 — golden anchor from spec §5 dictionary.

    instruction = $2,683,135,000
    institutional_support = $810,116,000
    endowment = $36,494,893,000
    FTE = 19,094
    Expected derivations:
      instruction_per_fte = 140,522.42
      institutional_support_per_fte = 42,427.59
      endowment_per_fte = 1,911,327.80
      marketing_ratio = 0.30192890033486947
    Expected record_id: ipf-267f20f48b4b772f
    """
    return {
        "unitid": 243744,
        "institution_name": "Stanford University",
        "report_form": "F1A",
        "fiscal_year": 2023,
        "institutional_support_expenses": 810_116_000.0,
        "instruction_expenses": 2_683_135_000.0,
        "endowment_value": 36_494_893_000.0,
        "total_fte_enrollment": 19_094.0,
        "load_date": LOAD_DATE,
        "ingested_at": INGESTED_AT,
        "source_url": "https://nces.ed.gov/ipeds/datacenter/data/F2223_F1A.zip|...",
        "source_method": "csv_cache",
    }


def _f3_bronze_row(unitid: int = 199193) -> dict:
    """F3 (for-profit) row — endowment is structurally NULL (no F3H family).

    Real reported F3 institution: instruction $50M, inst-support $55M, FTE 504.
    Expected: marketing_ratio = 1.10, endowment_per_fte = NULL.
    """
    return {
        "unitid": unitid,
        "institution_name": "For-Profit Online University",
        "report_form": "F3",
        "fiscal_year": 2023,
        "institutional_support_expenses": 55_000_000.0,
        "instruction_expenses": 50_000_000.0,
        "endowment_value": None,  # F3 has no F3H — structurally NULL
        "total_fte_enrollment": 504.0,
        "load_date": LOAD_DATE,
        "ingested_at": INGESTED_AT,
        "source_url": "...",
        "source_method": "csv_cache",
    }


def _zero_instruction_bronze_row() -> dict:
    """Synthetic system-administrative-office row with zero instruction.

    Per spec §5: such rows produce NULL marketing_ratio (NULLIF semantics),
    NOT a divide-by-zero error or 0.0."""
    return {
        "unitid": 999001,
        "institution_name": "System Admin Office",
        "report_form": "F1A",
        "fiscal_year": 2023,
        "institutional_support_expenses": 5_000_000.0,
        "instruction_expenses": 0.0,  # zero — triggers NULLIF
        "endowment_value": 1_000_000.0,
        "total_fte_enrollment": 100.0,
        "load_date": LOAD_DATE,
        "ingested_at": INGESTED_AT,
        "source_url": "...",
        "source_method": "csv_cache",
    }


# ---------------------------------------------------------------------------
# derive_per_fte — NULL cascades + zero/negative-FTE guard
# ---------------------------------------------------------------------------


class TestDerivePerFte:
    def test_returns_none_when_numerator_none(self):
        assert derive_per_fte(None, 100.0) is None

    def test_returns_none_when_fte_none(self):
        assert derive_per_fte(50_000.0, None) is None

    def test_returns_none_when_both_none(self):
        assert derive_per_fte(None, None) is None

    @pytest.mark.parametrize("fte", [0.0, -1.0, -100.0])
    def test_returns_none_when_fte_zero_or_negative(self, fte):
        """fte <= 0 produces NULL — guards against zero-FTE-administrative-office
        and any pathological negative-FTE that would silently produce a
        meaningless value."""
        assert derive_per_fte(50_000.0, fte) is None

    def test_correct_value_when_both_present(self):
        """100/10 = 10.0 — straight double division."""
        assert derive_per_fte(100.0, 10.0) == 10.0

    def test_stanford_instruction_per_fte(self):
        """Stanford: $2,683,135,000 / 19,094 FTE = $140,522.42."""
        result = derive_per_fte(2_683_135_000.0, 19_094.0)
        assert result == pytest.approx(140_522.42, abs=0.01)

    def test_arithmetic_invariant_roundtrip(self):
        """BSE-IPF-008: derive_per_fte(num, fte) * fte ≈ num within $1.

        This is the load-bearing arithmetic invariant — plain double math
        must round-trip perfectly to exact float equality for typical
        IPEDS values."""
        for num, fte in [
            (2_683_135_000.0, 19_094.0),  # Stanford instruction
            (810_116_000.0, 19_094.0),    # Stanford inst-support
            (36_494_893_000.0, 19_094.0),  # Stanford endowment
            (50_000_000.0, 504.0),         # F3 instruction
        ]:
            per_fte = derive_per_fte(num, fte)
            assert per_fte is not None
            assert abs(per_fte * fte - num) < 1.0


# ---------------------------------------------------------------------------
# derive_marketing_ratio — NULLIF semantics
# ---------------------------------------------------------------------------


class TestDeriveMarketingRatio:
    def test_correct_value(self):
        """30/100 = 0.30."""
        assert derive_marketing_ratio(30.0, 100.0) == 0.30

    def test_stanford_value(self):
        """Stanford: $810,116,000 / $2,683,135,000 ≈ 0.30193."""
        result = derive_marketing_ratio(810_116_000.0, 2_683_135_000.0)
        assert result == pytest.approx(0.30193, abs=1e-5)

    def test_returns_none_when_inst_supp_none(self):
        assert derive_marketing_ratio(None, 100.0) is None

    def test_returns_none_when_instruction_none(self):
        assert derive_marketing_ratio(30.0, None) is None

    def test_returns_none_when_both_none(self):
        assert derive_marketing_ratio(None, None) is None

    def test_returns_none_when_instruction_zero(self):
        """NULLIF(instruction, 0): zero instruction → NULL marketing_ratio.

        This guards the 34 system-admin-office rows in the FY23 corpus from
        producing a meaningless +Inf or division-by-zero error."""
        assert derive_marketing_ratio(5_000_000.0, 0.0) is None


# ---------------------------------------------------------------------------
# _to_optional_float — defensive NaN rejection
# ---------------------------------------------------------------------------


class TestToOptionalFloat:
    def test_none_returns_none(self):
        assert _to_optional_float(None) is None

    def test_int_returns_float(self):
        assert _to_optional_float(100) == 100.0

    def test_float_returns_float(self):
        assert _to_optional_float(1.5) == 1.5

    def test_nan_returns_none(self):
        """NaN must NOT propagate downstream — would corrupt arithmetic invariants."""
        assert _to_optional_float(float("nan")) is None

    def test_string_numeric_returns_float(self):
        assert _to_optional_float("123.45") == 123.45


# ---------------------------------------------------------------------------
# transform_row — missing required fields raise; record_id is deterministic
# ---------------------------------------------------------------------------


class TestTransformRowRequiredFields:
    """Spec §5 base requires unitid, institution_name, report_form,
    fiscal_year, load_date — each missing field must raise ValueError."""

    def test_missing_unitid_raises(self):
        row = _stanford_bronze_row()
        del row["unitid"]
        with pytest.raises(ValueError, match="unitid"):
            transform_row(row, ingested_at=INGESTED_AT)

    def test_missing_institution_name_raises(self):
        row = _stanford_bronze_row()
        del row["institution_name"]
        with pytest.raises(ValueError, match="institution_name"):
            transform_row(row, ingested_at=INGESTED_AT)

    def test_missing_report_form_raises(self):
        row = _stanford_bronze_row()
        del row["report_form"]
        with pytest.raises(ValueError, match="report_form"):
            transform_row(row, ingested_at=INGESTED_AT)

    def test_missing_fiscal_year_raises(self):
        row = _stanford_bronze_row()
        del row["fiscal_year"]
        with pytest.raises(ValueError, match="fiscal_year"):
            transform_row(row, ingested_at=INGESTED_AT)

    def test_missing_load_date_raises(self):
        row = _stanford_bronze_row()
        del row["load_date"]
        with pytest.raises(ValueError, match="load_date"):
            transform_row(row, ingested_at=INGESTED_AT)


class TestTransformRowDeterministic:
    def test_record_id_prefix_is_ipf(self):
        """Spec §5: record_id prefix is 'ipf' (NOT 'ifp' which is gold)."""
        row = transform_row(_stanford_bronze_row(), ingested_at=INGESTED_AT)
        assert row["record_id"].startswith("ipf-")

    def test_record_id_is_deterministic(self):
        """Same inputs → same record_id, every time."""
        r1 = transform_row(_stanford_bronze_row(), ingested_at=INGESTED_AT)
        r2 = transform_row(_stanford_bronze_row(), ingested_at=INGESTED_AT)
        assert r1["record_id"] == r2["record_id"]

    def test_stanford_record_id_exact(self):
        """Spec §5 + staff review: Stanford UNITID 243744 → ipf-267f20f48b4b772f.

        This is the load-bearing cross-zone hash check — same hash suffix
        must appear in consumable as ifp-267f20f48b4b772f."""
        row = transform_row(_stanford_bronze_row(), ingested_at=INGESTED_AT)
        assert row["record_id"] == "ipf-267f20f48b4b772f"

    def test_record_id_depends_only_on_unitid(self):
        """Mutating non-grain fields (institution_name, instruction_expenses)
        must NOT change the record_id."""
        r1 = transform_row(_stanford_bronze_row(), ingested_at=INGESTED_AT)
        mutated = _stanford_bronze_row()
        mutated["institution_name"] = "Changed Name"
        mutated["instruction_expenses"] = 1.0
        r2 = transform_row(mutated, ingested_at=INGESTED_AT)
        assert r1["record_id"] == r2["record_id"]


# ---------------------------------------------------------------------------
# transform_row — derivation correctness
# ---------------------------------------------------------------------------


class TestTransformRowDerivations:
    def test_stanford_derivations_exact(self):
        """Stanford golden-row: every derivation matches the spec §5 dictionary."""
        row = transform_row(_stanford_bronze_row(), ingested_at=INGESTED_AT)
        # Per-FTE
        assert row["instruction_per_fte"] == pytest.approx(140_522.42, abs=0.01)
        # $810,116,000 / 19,094 = 42,427.78 (verified)
        assert row["institutional_support_per_fte"] == pytest.approx(42_427.78, abs=0.01)
        assert row["endowment_per_fte"] == pytest.approx(1_911_327.80, abs=0.01)
        # Marketing ratio
        assert row["marketing_ratio"] == pytest.approx(0.30193, abs=1e-5)

    def test_passthrough_fields_preserved(self):
        """Raw dollar values pass through unchanged."""
        row = transform_row(_stanford_bronze_row(), ingested_at=INGESTED_AT)
        assert row["instruction_expenses"] == 2_683_135_000.0
        assert row["institutional_support_expenses"] == 810_116_000.0
        assert row["endowment_value"] == 36_494_893_000.0
        assert row["total_fte_enrollment"] == 19_094.0
        assert row["unitid"] == 243744
        assert row["institution_name"] == "Stanford University"
        assert row["report_form"] == "F1A"
        assert row["fiscal_year"] == 2023

    def test_provenance_fields(self):
        """source_load_date carries the bronze load_date; ingested_at uses override."""
        row = transform_row(_stanford_bronze_row(), ingested_at=INGESTED_AT)
        assert row["source_load_date"] == LOAD_DATE
        assert row["ingested_at"] == INGESTED_AT

    def test_arithmetic_invariant_bse_ipf_008(self):
        """BSE-IPF-008: instruction_per_fte * total_fte_enrollment ≈
        instruction_expenses within $1."""
        row = transform_row(_stanford_bronze_row(), ingested_at=INGESTED_AT)
        product = row["instruction_per_fte"] * row["total_fte_enrollment"]
        assert abs(product - row["instruction_expenses"]) < 1.0

    def test_arithmetic_invariant_bse_ipf_009_inst_supp(self):
        """BSE-IPF-009 (institutional_support arm)."""
        row = transform_row(_stanford_bronze_row(), ingested_at=INGESTED_AT)
        product = row["institutional_support_per_fte"] * row["total_fte_enrollment"]
        assert abs(product - row["institutional_support_expenses"]) < 1.0

    def test_arithmetic_invariant_bse_ipf_009_endowment(self):
        """BSE-IPF-009 (endowment arm)."""
        row = transform_row(_stanford_bronze_row(), ingested_at=INGESTED_AT)
        product = row["endowment_per_fte"] * row["total_fte_enrollment"]
        assert abs(product - row["endowment_value"]) < 1.0

    def test_arithmetic_invariant_bse_ipf_010(self):
        """BSE-IPF-010: marketing_ratio * instruction ≈ inst_supp within $1."""
        row = transform_row(_stanford_bronze_row(), ingested_at=INGESTED_AT)
        product = row["marketing_ratio"] * row["instruction_expenses"]
        assert abs(product - row["institutional_support_expenses"]) < 1.0


# ---------------------------------------------------------------------------
# F3 NULL-cascade + zero-instruction edge cases
# ---------------------------------------------------------------------------


class TestF3NullCascade:
    def test_f3_endowment_value_none_produces_null_endowment_per_fte(self):
        """F3 has no F3H family — endowment NULL must cascade to endowment_per_fte NULL."""
        row = transform_row(_f3_bronze_row(), ingested_at=INGESTED_AT)
        assert row["endowment_value"] is None
        assert row["endowment_per_fte"] is None

    def test_f3_other_derivations_still_populated(self):
        """F3 marketing_ratio + per-FTE values for instruction/inst-support
        should still derive — only endowment cascades to NULL."""
        row = transform_row(_f3_bronze_row(), ingested_at=INGESTED_AT)
        assert row["instruction_per_fte"] == pytest.approx(50_000_000.0 / 504.0, abs=0.01)
        assert row["institutional_support_per_fte"] == pytest.approx(
            55_000_000.0 / 504.0, abs=0.01
        )
        assert row["marketing_ratio"] == pytest.approx(1.10, abs=1e-3)


class TestZeroInstructionRow:
    def test_zero_instruction_produces_null_marketing_ratio(self):
        """System-admin-office rows with $0 instruction → NULL marketing_ratio
        (NULLIF semantics from spec §5 footnote)."""
        row = transform_row(_zero_instruction_bronze_row(), ingested_at=INGESTED_AT)
        assert row["instruction_expenses"] == 0.0
        assert row["marketing_ratio"] is None

    def test_zero_instruction_produces_zero_instruction_per_fte(self):
        """0 / fte = 0.0 (not NULL) — only marketing_ratio uses NULLIF."""
        row = transform_row(_zero_instruction_bronze_row(), ingested_at=INGESTED_AT)
        assert row["instruction_per_fte"] == 0.0


# ---------------------------------------------------------------------------
# transform_rows — duplicate-UNITID rejection + same-length output
# ---------------------------------------------------------------------------


class TestTransformRows:
    def test_returns_same_length(self):
        """Conservation invariant: every input row produces exactly one output row."""
        bronze = [_stanford_bronze_row(), _f3_bronze_row(199193), _zero_instruction_bronze_row()]
        base = transform_rows(bronze, ingested_at=INGESTED_AT)
        assert len(base) == 3

    def test_duplicate_unitid_raises_value_error(self):
        """Duplicate-grain bronze snapshot must fail loud at silver promote."""
        bronze = [_stanford_bronze_row(), _stanford_bronze_row()]  # both UNITID 243744
        with pytest.raises(ValueError, match="Duplicate unitid"):
            transform_rows(bronze, ingested_at=INGESTED_AT)

    def test_record_ids_unique(self):
        bronze = [_stanford_bronze_row(), _f3_bronze_row(199193), _zero_instruction_bronze_row()]
        base = transform_rows(bronze, ingested_at=INGESTED_AT)
        ids = [r["record_id"] for r in base]
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Schema — spec §5 base schema exactly
# ---------------------------------------------------------------------------


class TestBaseSchema:
    def test_get_base_schema_returns_schema(self):
        assert isinstance(get_base_schema(), Schema)

    def test_field_count(self):
        """Spec §5: 15 columns."""
        assert len(get_base_schema().fields) == 15

    def test_field_names_match_spec(self):
        names = [f.name for f in get_base_schema().fields]
        expected = [
            "record_id", "unitid", "institution_name", "report_form", "fiscal_year",
            "institutional_support_expenses", "instruction_expenses",
            "endowment_value", "total_fte_enrollment",
            "institutional_support_per_fte", "instruction_per_fte",
            "endowment_per_fte", "marketing_ratio",
            "source_load_date", "ingested_at",
        ]
        assert names == expected

    def test_required_vs_nullable(self):
        """Identity + provenance fields are required; numeric measures are nullable."""
        schema = get_base_schema()
        required_names = {f.name for f in schema.fields if f.required}
        nullable_names = {f.name for f in schema.fields if not f.required}
        for required in ("record_id", "unitid", "institution_name", "report_form",
                          "fiscal_year", "source_load_date", "ingested_at"):
            assert required in required_names
        # F3 endowment NULL means endowment_value can't be required
        assert "endowment_value" in nullable_names
        assert "endowment_per_fte" in nullable_names
        assert "marketing_ratio" in nullable_names

    def test_field_types(self):
        types_by_name = {f.name: type(f.field_type) for f in get_base_schema().fields}
        assert types_by_name["record_id"] is StringType
        assert types_by_name["unitid"] is LongType
        assert types_by_name["institution_name"] is StringType
        assert types_by_name["report_form"] is StringType
        assert types_by_name["fiscal_year"] is IntegerType
        assert types_by_name["institutional_support_expenses"] is DoubleType
        assert types_by_name["instruction_expenses"] is DoubleType
        assert types_by_name["endowment_value"] is DoubleType
        assert types_by_name["total_fte_enrollment"] is DoubleType
        assert types_by_name["institutional_support_per_fte"] is DoubleType
        assert types_by_name["instruction_per_fte"] is DoubleType
        assert types_by_name["endowment_per_fte"] is DoubleType
        assert types_by_name["marketing_ratio"] is DoubleType
        assert types_by_name["source_load_date"] is DateType
        assert types_by_name["ingested_at"] is TimestampType


class TestModuleConstants:
    def test_grain_fields(self):
        assert GRAIN_FIELDS == ["unitid"]

    def test_grain_prefix(self):
        """Spec §5: prefix is 'ipf' (distinct from gold's 'ifp')."""
        assert GRAIN_PREFIX == "ipf"

    def test_spec_name(self):
        assert SPEC_NAME == "base-ipeds-finance"


# ---------------------------------------------------------------------------
# Integration — bronze → base via promote_ipeds_finance_base
# ---------------------------------------------------------------------------


def _bronze_schema() -> Schema:
    """Minimal bronze schema sufficient for the silver transformer's reads."""
    return Schema(
        NestedField(1, "unitid", LongType(), required=True),
        NestedField(2, "institution_name", StringType(), required=True),
        NestedField(3, "report_form", StringType(), required=True),
        NestedField(4, "fiscal_year", IntegerType(), required=True),
        NestedField(5, "institutional_support_expenses", DoubleType(), required=False),
        NestedField(6, "instruction_expenses", DoubleType(), required=False),
        NestedField(7, "endowment_value", DoubleType(), required=False),
        NestedField(8, "total_fte_enrollment", DoubleType(), required=False),
        NestedField(9, "source_url", StringType(), required=True),
        NestedField(10, "source_method", StringType(), required=True),
        NestedField(11, "ingested_at", TimestampType(), required=True),
        NestedField(12, "load_date", DateType(), required=True),
    )


def _seed_temp_bronze(tmp_path: Path, bronze_rows: list[dict]) -> tuple[Path, Path, Path]:
    """Create a temp Iceberg warehouse with a seeded bronze.ipeds_finance table."""
    from brightsmith.infra.iceberg_setup import (
        append_data,
        get_catalog,
        get_or_create_table,
    )

    bronze_warehouse = tmp_path / "bronze"
    base_warehouse = tmp_path / "silver"
    catalog_path = tmp_path / "catalog.db"
    bronze_warehouse.mkdir(parents=True, exist_ok=True)
    base_warehouse.mkdir(parents=True, exist_ok=True)

    catalog = get_catalog(bronze_warehouse, catalog_path)
    table = get_or_create_table(catalog, "bronze", "ipeds_finance", _bronze_schema())
    append_data(table, bronze_rows)
    return bronze_warehouse, base_warehouse, catalog_path


class TestIntegration:
    def test_end_to_end_3_rows(self, tmp_path):
        """End-to-end promote: 3 bronze rows → 3 base rows with full derivations."""
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        bronze = [_stanford_bronze_row(), _f3_bronze_row(199193),
                  _zero_instruction_bronze_row()]
        bronze_wh, base_wh, catalog_path = _seed_temp_bronze(tmp_path, bronze)

        result = promote_ipeds_finance_base(
            bronze_warehouse=bronze_wh,
            base_warehouse=base_wh,
            catalog_path=catalog_path,
            ingested_at=INGESTED_AT,
        )
        assert result["rows_read"] == 3
        assert result["rows_transformed"] == 3
        assert result["promoted"] == 3
        assert result["skipped_dedup"] == 0

        catalog = get_catalog(base_wh, catalog_path)
        rows = read_with_duckdb(catalog.load_table(f"{BASE_NAMESPACE}.{BASE_TABLE_NAME}"))
        assert len(rows) == 3

        # Stanford anchor
        stanford = next(r for r in rows if r["unitid"] == 243744)
        assert stanford["record_id"] == "ipf-267f20f48b4b772f"
        assert stanford["marketing_ratio"] == pytest.approx(0.30193, abs=1e-5)
        assert stanford["instruction_per_fte"] == pytest.approx(140_522.42, abs=0.01)

        # F3 NULL cascade
        f3 = next(r for r in rows if r["unitid"] == 199193)
        assert f3["endowment_value"] is None
        assert f3["endowment_per_fte"] is None

        # Zero-instruction NULL marketing_ratio
        admin = next(r for r in rows if r["unitid"] == 999001)
        assert admin["marketing_ratio"] is None

    def test_idempotent_second_run(self, tmp_path):
        """Spec §5: re-running with same bronze snapshot produces 0 new rows."""
        bronze = [_stanford_bronze_row(), _f3_bronze_row(199193)]
        bronze_wh, base_wh, catalog_path = _seed_temp_bronze(tmp_path, bronze)

        r1 = promote_ipeds_finance_base(
            bronze_warehouse=bronze_wh, base_warehouse=base_wh,
            catalog_path=catalog_path, ingested_at=INGESTED_AT,
        )
        assert r1["promoted"] == 2

        r2 = promote_ipeds_finance_base(
            bronze_warehouse=bronze_wh, base_warehouse=base_wh,
            catalog_path=catalog_path, ingested_at=INGESTED_AT,
        )
        assert r2["promoted"] == 0
        assert r2["skipped_dedup"] == 2

    def test_form_mix_logged(self, tmp_path):
        """Form-mix counter must reflect bronze form distribution."""
        bronze = [
            _stanford_bronze_row(),         # F1A
            _f3_bronze_row(199193),         # F3
            _zero_instruction_bronze_row(),  # F1A
        ]
        bronze_wh, base_wh, catalog_path = _seed_temp_bronze(tmp_path, bronze)

        result = promote_ipeds_finance_base(
            bronze_warehouse=bronze_wh, base_warehouse=base_wh,
            catalog_path=catalog_path, ingested_at=INGESTED_AT,
        )
        assert result["form_counts"]["F1A"] == 2
        assert result["form_counts"]["F3"] == 1
