"""Tests for the Gold/consumable IPEDS Finance profile transformer.

Covers:
  - classify_data_completeness_tier: 5 enum cases (high/medium/low/insufficient
    + the FTE > 0 not-a-signal guard)
  - F3 medium-not-high invariant (load-bearing v1.2 reviewer rework)
  - F3 medium-not-low boundary case
  - transform_row: passthrough verbatim + ifp- prefix + cross-zone hash
    separation (ipf- vs ifp-)
  - transform_rows: duplicate-UNITID rejection + same-length output +
    same promoted_at across batch
  - Stanford golden-row (UNITID 243744 → ifp-267f20f48b4b772f, tier=high)
  - Schema (15 fields, dense IDs, exact column names + v1.2 raw passthroughs)
  - CON-IFP-007 arithmetic invariant (carry-forward from base, not recomputed)
  - Integration: base → consumable end-to-end via transform()

Per the staff-engineer canonical test list (governance/approvals/
full-pipeline-ipeds-finance-staff-review.md): 15 consumable assertions minimum.
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

from gold.ipeds_finance_profile import (
    BASE_PASSTHROUGH_FIELDS,
    CONSUMABLE_NAMESPACE,
    CONSUMABLE_TABLE_NAME,
    GRAIN_FIELDS,
    GRAIN_PREFIX,
    SPEC_NAME,
    TIER_RAW_INPUTS,
    classify_data_completeness_tier,
    get_consumable_schema,
    transform,
    transform_row,
    transform_rows,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


PROMOTED_AT = datetime.datetime(2026, 4, 30, 12, 0, 0, tzinfo=datetime.timezone.utc)
LOAD_DATE = datetime.date(2026, 4, 30)
INGESTED_AT = datetime.datetime(2026, 4, 30, 11, 0, 0, tzinfo=datetime.timezone.utc)


def _stanford_base_row() -> dict:
    """Stanford anchor (UNITID 243744) — all 4 raw inputs present → high tier.

    Pre-derived per-FTE + marketing_ratio match what base produced.
    Expected consumable record_id: ifp-267f20f48b4b772f."""
    return {
        "record_id": "ipf-267f20f48b4b772f",  # base record_id; consumable rederives
        "unitid": 243744,
        "institution_name": "Stanford University",
        "report_form": "F1A",
        "fiscal_year": 2023,
        "institutional_support_expenses": 810_116_000.0,
        "instruction_expenses": 2_683_135_000.0,
        "endowment_value": 36_494_893_000.0,
        "total_fte_enrollment": 19_094.0,
        "institutional_support_per_fte": 810_116_000.0 / 19_094.0,
        "instruction_per_fte": 2_683_135_000.0 / 19_094.0,
        "endowment_per_fte": 36_494_893_000.0 / 19_094.0,
        "marketing_ratio": 810_116_000.0 / 2_683_135_000.0,
        "source_load_date": LOAD_DATE,
        "ingested_at": INGESTED_AT,
    }


def _f3_base_row(unitid: int = 199193) -> dict:
    """F3 row — endowment NULL by structure → medium tier (3/4 inputs)."""
    return {
        "record_id": "ipf-fakehash00000001",
        "unitid": unitid,
        "institution_name": "For-Profit Online U",
        "report_form": "F3",
        "fiscal_year": 2023,
        "institutional_support_expenses": 55_000_000.0,
        "instruction_expenses": 50_000_000.0,
        "endowment_value": None,  # F3 has no F3H
        "total_fte_enrollment": 504.0,
        "institutional_support_per_fte": 55_000_000.0 / 504.0,
        "instruction_per_fte": 50_000_000.0 / 504.0,
        "endowment_per_fte": None,
        "marketing_ratio": 55_000_000.0 / 50_000_000.0,
        "source_load_date": LOAD_DATE,
        "ingested_at": INGESTED_AT,
    }


# ---------------------------------------------------------------------------
# classify_data_completeness_tier — 5 enum cases + boundary guards
# ---------------------------------------------------------------------------


class TestClassifyDataCompletenessTier:
    """v1.2 formula counts the 4 INDEPENDENT raw inputs:
    instruction_expenses, institutional_support_expenses, endowment_value,
    total_fte_enrollment (positive). NOT derived signals."""

    def test_high_when_all_4_inputs_present(self):
        row = {
            "instruction_expenses": 100.0,
            "institutional_support_expenses": 50.0,
            "endowment_value": 1000.0,
            "total_fte_enrollment": 10.0,
        }
        assert classify_data_completeness_tier(row) == "high"

    def test_medium_when_3_inputs_present(self):
        row = {
            "instruction_expenses": 100.0,
            "institutional_support_expenses": 50.0,
            "endowment_value": None,
            "total_fte_enrollment": 10.0,
        }
        assert classify_data_completeness_tier(row) == "medium"

    def test_medium_when_2_inputs_present(self):
        """The lower bound of medium: 2/4 → medium."""
        row = {
            "instruction_expenses": 100.0,
            "institutional_support_expenses": None,
            "endowment_value": None,
            "total_fte_enrollment": 10.0,
        }
        assert classify_data_completeness_tier(row) == "medium"

    def test_low_when_1_input_present(self):
        row = {
            "instruction_expenses": 100.0,
            "institutional_support_expenses": None,
            "endowment_value": None,
            "total_fte_enrollment": None,
        }
        assert classify_data_completeness_tier(row) == "low"

    def test_insufficient_when_0_inputs_present(self):
        row = {
            "instruction_expenses": None,
            "institutional_support_expenses": None,
            "endowment_value": None,
            "total_fte_enrollment": None,
        }
        assert classify_data_completeness_tier(row) == "insufficient"

    @pytest.mark.parametrize("fte", [0.0, -1.0, -100.0])
    def test_zero_or_negative_fte_not_a_signal(self, fte):
        """FTE <= 0 makes per-FTE values NULL → not counted as a usable signal.

        Without this guard, an institution with FTE=0 + 3 dollar fields would
        misleadingly land at 'high' even though every per-FTE value cascades
        to NULL."""
        row = {
            "instruction_expenses": 100.0,
            "institutional_support_expenses": 50.0,
            "endowment_value": 1000.0,
            "total_fte_enrollment": fte,
        }
        # 3 inputs counted (not 4) — FTE=0 is not a signal
        assert classify_data_completeness_tier(row) == "medium"


class TestF3MediumNotHighInvariant:
    """Load-bearing invariant from spec §6.2 v1.2 reviewer rework:
    F3 institutions can NEVER classify as 'high' (endowment NULL by structure)."""

    def test_f3_with_3_inputs_lands_medium(self):
        """F3 + instruction + inst_supp + FTE present (3/4) → medium, NOT high."""
        row = _f3_base_row()
        assert row["endowment_value"] is None  # baseline check
        assert classify_data_completeness_tier(row) == "medium"

    def test_f3_can_never_be_high(self):
        """Regression guard: even with most-favorable F3 data (3 inputs present),
        tier must be 'medium' — high requires endowment_value non-null which
        is structurally impossible on F3."""
        # Try every combination of present/absent on the 3 non-endowment fields
        # F3 endowment is locked None.
        for instr in [100.0, None]:
            for inst_supp in [50.0, None]:
                for fte in [10.0, None]:
                    row = {
                        "instruction_expenses": instr,
                        "institutional_support_expenses": inst_supp,
                        "endowment_value": None,  # F3 invariant
                        "total_fte_enrollment": fte,
                    }
                    assert classify_data_completeness_tier(row) != "high"

    def test_f3_with_only_one_other_input_lands_low(self):
        """F3 boundary: only 1 other raw input present → low tier (1/4)."""
        row = {
            "instruction_expenses": 100.0,
            "institutional_support_expenses": None,
            "endowment_value": None,
            "total_fte_enrollment": None,
        }
        assert classify_data_completeness_tier(row) == "low"


class TestTierRawInputsConstant:
    def test_exactly_four_raw_inputs(self):
        """Spec §6.2: exactly 4 independent raw inputs."""
        assert len(TIER_RAW_INPUTS) == 4

    def test_raw_inputs_match_spec(self):
        assert set(TIER_RAW_INPUTS) == {
            "instruction_expenses",
            "institutional_support_expenses",
            "endowment_value",
            "total_fte_enrollment",
        }

    def test_does_not_include_derived_fields(self):
        """v1.2 rework: NO derived signals (marketing_ratio, per-FTE)
        in the tier formula — would double-count expense fields."""
        for derived in ("marketing_ratio", "instruction_per_fte",
                        "institutional_support_per_fte", "endowment_per_fte"):
            assert derived not in TIER_RAW_INPUTS


# ---------------------------------------------------------------------------
# transform_row — passthrough + ifp prefix + record_id determinism
# ---------------------------------------------------------------------------


class TestTransformRow:
    def test_record_id_prefix_is_ifp(self):
        """Spec §6: record_id prefix is 'ifp' (NOT 'ipf' which is base)."""
        row = transform_row(_stanford_base_row(), promoted_at=PROMOTED_AT)
        assert row["record_id"].startswith("ifp-")

    def test_record_id_is_deterministic(self):
        r1 = transform_row(_stanford_base_row(), promoted_at=PROMOTED_AT)
        r2 = transform_row(_stanford_base_row(), promoted_at=PROMOTED_AT)
        assert r1["record_id"] == r2["record_id"]

    def test_stanford_record_id_exact(self):
        """Spec §6 + staff review: Stanford UNITID 243744 → ifp-267f20f48b4b772f."""
        row = transform_row(_stanford_base_row(), promoted_at=PROMOTED_AT)
        assert row["record_id"] == "ifp-267f20f48b4b772f"

    def test_passthrough_verbatim(self):
        """All BASE_PASSTHROUGH_FIELDS carry forward unchanged."""
        base = _stanford_base_row()
        consumable = transform_row(base, promoted_at=PROMOTED_AT)
        for field in BASE_PASSTHROUGH_FIELDS:
            assert consumable[field] == base[field], f"{field} drifted from base"

    def test_promoted_at_stamped(self):
        row = transform_row(_stanford_base_row(), promoted_at=PROMOTED_AT)
        assert row["promoted_at"] == PROMOTED_AT
        assert row["promoted_at"] is not None

    def test_data_completeness_tier_synthesized(self):
        """Stanford has all 4 raw inputs → high tier."""
        row = transform_row(_stanford_base_row(), promoted_at=PROMOTED_AT)
        assert row["data_completeness_tier"] == "high"

    def test_f3_synthesizes_medium_tier(self):
        """F3 row with NULL endowment + other 3 present → medium."""
        row = transform_row(_f3_base_row(), promoted_at=PROMOTED_AT)
        assert row["data_completeness_tier"] == "medium"

    def test_no_arithmetic_recomputation(self):
        """Per spec §6: consumable does NOT recompute marketing_ratio or
        per-FTE values — they pass through from base verbatim. CON-IFP-007
        arithmetic invariant is upstream of this transformer."""
        base = _stanford_base_row()
        consumable = transform_row(base, promoted_at=PROMOTED_AT)
        assert consumable["marketing_ratio"] == base["marketing_ratio"]
        assert consumable["instruction_per_fte"] == base["instruction_per_fte"]
        assert consumable["institutional_support_per_fte"] == base["institutional_support_per_fte"]
        assert consumable["endowment_per_fte"] == base["endowment_per_fte"]


# ---------------------------------------------------------------------------
# Cross-zone hash separation — ipf vs ifp prefixes, same suffix
# ---------------------------------------------------------------------------


class TestCrossZoneHashSeparation:
    """Same-UNITID base record_id (ipf-…) and consumable record_id (ifp-…)
    must differ ONLY in the prefix. The hash suffix matches by construction
    because both grain_fields = ['unitid']."""

    def test_stanford_hash_suffix_matches_base(self):
        """Stanford 243744: base ipf-267f20f48b4b772f / consumable ifp-267f20f48b4b772f.

        Same hash, different prefix — proven manually via compute_grain_id."""
        consumable = transform_row(_stanford_base_row(), promoted_at=PROMOTED_AT)
        assert consumable["record_id"] == "ifp-267f20f48b4b772f"
        # The suffix matches base's ipf-267f20f48b4b772f (verified in
        # tests/silver/test_ipeds_finance_base.py::test_stanford_record_id_exact).
        suffix = consumable["record_id"].split("-", 1)[1]
        assert suffix == "267f20f48b4b772f"

    def test_zone_prefixes_distinct(self):
        """Spec §6: GRAIN_PREFIX='ifp' (consumable) ≠ 'ipf' (base)."""
        assert GRAIN_PREFIX == "ifp"
        # Reverse-spell guard so a typo can't silently align them
        assert GRAIN_PREFIX != "ipf"


# ---------------------------------------------------------------------------
# transform_rows — duplicate UNITID + same length + shared promoted_at
# ---------------------------------------------------------------------------


class TestTransformRows:
    def test_returns_same_length(self):
        """Conservation invariant: every base row produces exactly one
        consumable row (CON-IFP-001 row count == base row count)."""
        base = [_stanford_base_row(), _f3_base_row()]
        consumable = transform_rows(base, promoted_at=PROMOTED_AT)
        assert len(consumable) == 2

    def test_duplicate_unitid_raises(self):
        """CON-IFP-003 uniqueness: duplicate UNITIDs in base must fail loud."""
        base = [_stanford_base_row(), _stanford_base_row()]  # both UNITID 243744
        with pytest.raises(ValueError, match="Duplicate unitid"):
            transform_rows(base, promoted_at=PROMOTED_AT)

    def test_shared_promoted_at_across_batch(self):
        """A single batch must carry one consistent promoted_at across all rows."""
        base = [_stanford_base_row(), _f3_base_row(199193), _f3_base_row(199194)]
        consumable = transform_rows(base, promoted_at=PROMOTED_AT)
        timestamps = {r["promoted_at"] for r in consumable}
        assert len(timestamps) == 1
        assert timestamps == {PROMOTED_AT}

    def test_default_promoted_at_used_when_none(self):
        """Per spec §6: default to datetime.now(tz=UTC) if not supplied."""
        base = [_stanford_base_row()]
        before = datetime.datetime.now(tz=datetime.timezone.utc)
        consumable = transform_rows(base, promoted_at=None)
        after = datetime.datetime.now(tz=datetime.timezone.utc)
        # promoted_at must have been auto-stamped within this call's window
        assert before <= consumable[0]["promoted_at"] <= after


# ---------------------------------------------------------------------------
# Schema — spec §6 consumable schema exactly (15 fields incl. v1.2 raw passthroughs)
# ---------------------------------------------------------------------------


class TestConsumableSchema:
    def test_get_consumable_schema_returns_schema(self):
        assert isinstance(get_consumable_schema(), Schema)

    def test_field_count(self):
        """Spec §6: 15 columns including the 4 raw passthroughs added in v1.1/v1.2."""
        assert len(get_consumable_schema().fields) == 15

    def test_field_names_match_spec(self):
        names = [f.name for f in get_consumable_schema().fields]
        expected = [
            "record_id", "unitid", "institution_name", "report_form", "fiscal_year",
            "total_fte_enrollment", "instruction_expenses",
            "institutional_support_expenses", "endowment_value",
            "institutional_support_per_fte", "instruction_per_fte",
            "endowment_per_fte", "marketing_ratio",
            "data_completeness_tier", "promoted_at",
        ]
        assert names == expected

    def test_v1_2_raw_passthroughs_present(self):
        """v1.1/v1.2 ADV-6 adds raw expense passthroughs at consumable so
        downstream specs (notably raw-ingest-eada.md) can compute composite
        ratios without back-joining to base."""
        names = {f.name for f in get_consumable_schema().fields}
        for raw_field in (
            "instruction_expenses",
            "institutional_support_expenses",
            "endowment_value",
            "total_fte_enrollment",
        ):
            assert raw_field in names, f"v1.2 raw passthrough {raw_field} missing"

    def test_data_completeness_tier_required(self):
        schema = get_consumable_schema()
        tier_field = next(
            f for f in schema.fields if f.name == "data_completeness_tier"
        )
        assert tier_field.required

    def test_promoted_at_required(self):
        schema = get_consumable_schema()
        promoted_field = next(f for f in schema.fields if f.name == "promoted_at")
        assert promoted_field.required

    def test_endowment_value_nullable(self):
        """F3 rows have NULL endowment — column must be nullable."""
        schema = get_consumable_schema()
        endow_field = next(f for f in schema.fields if f.name == "endowment_value")
        assert not endow_field.required

    def test_field_types(self):
        types = {f.name: type(f.field_type) for f in get_consumable_schema().fields}
        assert types["record_id"] is StringType
        assert types["unitid"] is LongType
        assert types["data_completeness_tier"] is StringType
        assert types["promoted_at"] is TimestampType
        assert types["fiscal_year"] is IntegerType
        assert types["instruction_expenses"] is DoubleType
        assert types["marketing_ratio"] is DoubleType


class TestModuleConstants:
    def test_grain_fields(self):
        assert GRAIN_FIELDS == ["unitid"]

    def test_grain_prefix_is_ifp(self):
        """Spec §6: prefix is 'ifp' (distinct from base's 'ipf')."""
        assert GRAIN_PREFIX == "ifp"

    def test_spec_name(self):
        assert SPEC_NAME == "consumable-ipeds-finance-profile"

    def test_base_passthrough_fields_count(self):
        """Spec §6: 12 fields pass through verbatim from base."""
        assert len(BASE_PASSTHROUGH_FIELDS) == 12

    def test_base_passthrough_excludes_derived_only(self):
        """BASE_PASSTHROUGH_FIELDS includes raw + derived; excludes
        record_id, source_load_date, ingested_at (zone-local provenance)."""
        for excluded in ("record_id", "source_load_date", "ingested_at"):
            assert excluded not in BASE_PASSTHROUGH_FIELDS


# ---------------------------------------------------------------------------
# CON-IFP-007 — arithmetic invariant carry-forward
# ---------------------------------------------------------------------------


class TestArithmeticInvariantCarryForward:
    """CON-IFP-007: institutional_support_per_fte / instruction_per_fte ≈
    marketing_ratio within 0.001 where all three non-null. The consumable
    transformer does NOT recompute these — invariant is satisfied by
    construction because they pass through from base."""

    def test_stanford_invariant_holds(self):
        row = transform_row(_stanford_base_row(), promoted_at=PROMOTED_AT)
        ratio_from_per_fte = row["institutional_support_per_fte"] / row["instruction_per_fte"]
        assert abs(ratio_from_per_fte - row["marketing_ratio"]) < 0.001

    def test_f3_invariant_holds(self):
        row = transform_row(_f3_base_row(), promoted_at=PROMOTED_AT)
        ratio_from_per_fte = row["institutional_support_per_fte"] / row["instruction_per_fte"]
        assert abs(ratio_from_per_fte - row["marketing_ratio"]) < 0.001


# ---------------------------------------------------------------------------
# Integration — base → consumable via transform()
# ---------------------------------------------------------------------------


def _base_schema() -> Schema:
    """Mirror of silver.ipeds_finance_base.get_base_schema() — 15 columns."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "unitid", LongType(), required=True),
        NestedField(3, "institution_name", StringType(), required=True),
        NestedField(4, "report_form", StringType(), required=True),
        NestedField(5, "fiscal_year", IntegerType(), required=True),
        NestedField(6, "institutional_support_expenses", DoubleType(), required=False),
        NestedField(7, "instruction_expenses", DoubleType(), required=False),
        NestedField(8, "endowment_value", DoubleType(), required=False),
        NestedField(9, "total_fte_enrollment", DoubleType(), required=False),
        NestedField(10, "institutional_support_per_fte", DoubleType(), required=False),
        NestedField(11, "instruction_per_fte", DoubleType(), required=False),
        NestedField(12, "endowment_per_fte", DoubleType(), required=False),
        NestedField(13, "marketing_ratio", DoubleType(), required=False),
        NestedField(14, "source_load_date", DateType(), required=True),
        NestedField(15, "ingested_at", TimestampType(), required=True),
    )


def _seed_temp_base(tmp_path: Path, base_rows: list[dict]) -> Path:
    """Seed a temp Iceberg warehouse with a base.ipeds_finance table."""
    from brightsmith.infra.iceberg_setup import (
        append_data,
        get_catalog,
        get_or_create_table,
    )

    project_dir = tmp_path / "project"
    base_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    consumable_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
    catalog_dir = project_dir / "data" / "catalog"
    base_warehouse.mkdir(parents=True, exist_ok=True)
    consumable_warehouse.mkdir(parents=True, exist_ok=True)
    catalog_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = catalog_dir / "catalog.db"

    catalog = get_catalog(base_warehouse, catalog_path)
    table = get_or_create_table(catalog, "base", "ipeds_finance", _base_schema())
    append_data(table, base_rows)
    return project_dir


class TestIntegration:
    def test_end_to_end_3_rows(self, tmp_path):
        """End-to-end base → consumable: 3 rows in / 3 rows out, deterministic IDs."""
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        # Add a low-tier row so we exercise the formula across a tier range
        low_tier_row = {
            **_stanford_base_row(),
            "unitid": 555000,
            "institution_name": "Low-Data University",
            "instruction_expenses": 100.0,
            "institutional_support_expenses": None,
            "endowment_value": None,
            "total_fte_enrollment": None,
            "institutional_support_per_fte": None,
            "instruction_per_fte": None,
            "endowment_per_fte": None,
            "marketing_ratio": None,
        }
        base = [_stanford_base_row(), _f3_base_row(199193), low_tier_row]
        project_dir = _seed_temp_base(tmp_path, base)

        result = transform(project_dir=project_dir, promoted_at=PROMOTED_AT)
        assert result["rows_read"] == 3
        assert result["rows_transformed"] == 3
        assert result["promoted"] == 3

        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        rows = read_with_duckdb(
            catalog.load_table(f"{CONSUMABLE_NAMESPACE}.{CONSUMABLE_TABLE_NAME}")
        )
        assert len(rows) == 3

        by_unitid = {r["unitid"]: r for r in rows}
        # Stanford → high
        assert by_unitid[243744]["data_completeness_tier"] == "high"
        assert by_unitid[243744]["record_id"] == "ifp-267f20f48b4b772f"
        # F3 → medium
        assert by_unitid[199193]["data_completeness_tier"] == "medium"
        # Low-data → low (only 1 raw input present)
        assert by_unitid[555000]["data_completeness_tier"] == "low"

    def test_idempotent_second_run(self, tmp_path):
        """Spec §6: re-running with same base snapshot produces 0 new rows."""
        base = [_stanford_base_row(), _f3_base_row()]
        project_dir = _seed_temp_base(tmp_path, base)

        r1 = transform(project_dir=project_dir, promoted_at=PROMOTED_AT)
        assert r1["promoted"] == 2

        r2 = transform(project_dir=project_dir, promoted_at=PROMOTED_AT)
        assert r2["promoted"] == 0
        assert r2["skipped_dedup"] == 2

    def test_tier_distribution_logged(self, tmp_path):
        base = [_stanford_base_row(), _f3_base_row(199193), _f3_base_row(199194)]
        project_dir = _seed_temp_base(tmp_path, base)

        result = transform(project_dir=project_dir, promoted_at=PROMOTED_AT)
        # 1 high (Stanford) + 2 medium (F3 with 3 raw inputs)
        assert result["tier_counts"]["high"] == 1
        assert result["tier_counts"]["medium"] == 2
