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
    SYSTEM_OFFICE_FTE_THRESHOLD,
    SYSTEM_OFFICE_INSTRUCTION_THRESHOLD,
    SYSTEM_OFFICE_NAME_PATTERNS,
    TIER_RAW_INPUTS,
    _name_matches_system_office_pattern,
    classify_data_completeness_tier,
    get_consumable_schema,
    is_system_office_row,
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
    Expected consumable record_id: ifp-267f20f48b4b772f.

    v1.4: ``endowment_value_flag = 'R'`` (institution-reported).
    """
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
        "endowment_value_flag": "R",  # v1.4
    }


def _f3_base_row(unitid: int = 199193) -> dict:
    """F3 row — endowment NULL by structure → medium tier (3/4 inputs).

    v1.4: ``endowment_value_flag = None`` (structural — no F3H family).
    """
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
        "endowment_value_flag": None,  # v1.4: F3 structural
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
        """Spec §6 (v1.4): 17 columns (15 v1.3 + endowment_value_provenance + source_load_date)."""
        assert len(get_consumable_schema().fields) == 17

    def test_field_names_match_spec(self):
        names = [f.name for f in get_consumable_schema().fields]
        expected = [
            "record_id", "unitid", "institution_name", "report_form", "fiscal_year",
            "total_fte_enrollment", "instruction_expenses",
            "institutional_support_expenses", "endowment_value",
            "institutional_support_per_fte", "instruction_per_fte",
            "endowment_per_fte", "marketing_ratio",
            "data_completeness_tier", "promoted_at",
            # v1.4 §6 additions (field-ids 16, 17)
            "endowment_value_provenance", "source_load_date",
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
        record_id, source_load_date, ingested_at (zone-local provenance).

        v1.4: ``source_load_date`` is restored as a passthrough at consumable
        per §2 Decision G but NOT through ``BASE_PASSTHROUGH_FIELDS`` — it's
        wired in ``transform_row`` directly.  Likewise
        ``endowment_value_flag`` is renamed (not pure passthrough), so it
        is also handled outside ``BASE_PASSTHROUGH_FIELDS``.
        """
        for excluded in (
            "record_id",
            "source_load_date",
            "ingested_at",
            "endowment_value_flag",
        ):
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
    """Mirror of silver.ipeds_finance_base.get_base_schema() — 16 columns (v1.4)."""
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
        # v1.4 §5 addition (field-id 16)
        NestedField(16, "endowment_value_flag", StringType(), required=False),
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


# ---------------------------------------------------------------------------
# v1.4 §6 — endowment_value_provenance rename + source_load_date passthrough
# ---------------------------------------------------------------------------


def _f1a_a_provenance_base_row(unitid: int = 100001) -> dict:
    """F1A row with flag = 'A' — endowment_value MUST be NULL (A↔NULL coupling)."""
    return {
        "record_id": "ipf-fakehash00000002",
        "unitid": unitid,
        "institution_name": "Test Community College",
        "report_form": "F1A",
        "fiscal_year": 2023,
        "institutional_support_expenses": 5_000_000.0,
        "instruction_expenses": 30_000_000.0,
        "endowment_value": None,  # A↔NULL
        "total_fte_enrollment": 2_000.0,
        "institutional_support_per_fte": 5_000_000.0 / 2_000.0,
        "instruction_per_fte": 30_000_000.0 / 2_000.0,
        "endowment_per_fte": None,
        "marketing_ratio": 5_000_000.0 / 30_000_000.0,
        "source_load_date": LOAD_DATE,
        "ingested_at": INGESTED_AT,
        "endowment_value_flag": "A",
    }


def _f2_n_provenance_base_row(unitid: int = 100002) -> dict:
    """F2 row with flag = 'N' (Imputed Nearest Neighbor) and populated value."""
    return {
        "record_id": "ipf-fakehash00000003",
        "unitid": unitid,
        "institution_name": "Test Private Nonprofit College",
        "report_form": "F2",
        "fiscal_year": 2023,
        "institutional_support_expenses": 8_000_000.0,
        "instruction_expenses": 25_000_000.0,
        "endowment_value": 50_000_000.0,
        "total_fte_enrollment": 1_500.0,
        "institutional_support_per_fte": 8_000_000.0 / 1_500.0,
        "instruction_per_fte": 25_000_000.0 / 1_500.0,
        "endowment_per_fte": 50_000_000.0 / 1_500.0,
        "marketing_ratio": 8_000_000.0 / 25_000_000.0,
        "source_load_date": LOAD_DATE,
        "ingested_at": INGESTED_AT,
        "endowment_value_flag": "N",
    }


class TestEndowmentValueProvenanceRename:
    """v1.4 §2 Decision A: base ``endowment_value_flag`` is exposed at
    consumable as ``endowment_value_provenance`` (renamed for consumer
    clarity).  CON-IFP-013 asserts passthrough fidelity."""

    def test_r_flag_lands_as_provenance(self):
        """Stanford's ``flag='R'`` lands at consumable as ``provenance='R'``."""
        row = transform_row(_stanford_base_row(), promoted_at=PROMOTED_AT)
        assert row["endowment_value_provenance"] == "R"

    def test_a_flag_lands_as_provenance(self):
        """``flag='A'`` lands as ``provenance='A'``."""
        row = transform_row(_f1a_a_provenance_base_row(), promoted_at=PROMOTED_AT)
        assert row["endowment_value_provenance"] == "A"

    def test_n_flag_lands_as_provenance(self):
        """``flag='N'`` lands as ``provenance='N'``."""
        row = transform_row(_f2_n_provenance_base_row(), promoted_at=PROMOTED_AT)
        assert row["endowment_value_provenance"] == "N"

    def test_f3_null_flag_lands_as_null_provenance(self):
        """F3 ``flag=None`` (structural) lands as ``provenance=None``."""
        row = transform_row(_f3_base_row(), promoted_at=PROMOTED_AT)
        assert row["endowment_value_provenance"] is None

    @pytest.mark.parametrize("flag", ["R", "A", "N", "P", "Z"])
    def test_all_five_codes_round_trip(self, flag):
        """Every code in the FY2023 observed domain {R, A, P, Z, N} round-trips."""
        base = _stanford_base_row()
        base["endowment_value_flag"] = flag
        row = transform_row(base, promoted_at=PROMOTED_AT)
        assert row["endowment_value_provenance"] == flag

    def test_old_flag_name_not_emitted_at_consumable(self):
        """v1.4 §2 Decision A: consumable does NOT emit ``endowment_value_flag``."""
        row = transform_row(_stanford_base_row(), promoted_at=PROMOTED_AT)
        assert "endowment_value_flag" not in row


class TestSourceLoadDatePassthrough:
    """v1.4 §2 Decision G: ``source_load_date`` is restored at consumable
    as a passthrough from base, NOT NULL.  CON-IFP-015 asserts 100%
    non-null."""

    def test_source_load_date_present(self):
        row = transform_row(_stanford_base_row(), promoted_at=PROMOTED_AT)
        assert row["source_load_date"] == LOAD_DATE

    def test_source_load_date_matches_base(self):
        """Consumable carries the exact base value verbatim — no re-derive."""
        base = _stanford_base_row()
        custom_date = datetime.date(2026, 1, 15)
        base["source_load_date"] = custom_date
        row = transform_row(base, promoted_at=PROMOTED_AT)
        assert row["source_load_date"] == custom_date

    def test_source_load_date_distinct_from_promoted_at(self):
        """source_load_date documents bronze-load time; promoted_at
        documents consumable-promote time.  They are distinct."""
        row = transform_row(_stanford_base_row(), promoted_at=PROMOTED_AT)
        assert row["source_load_date"] == LOAD_DATE
        assert row["promoted_at"] == PROMOTED_AT
        assert row["source_load_date"] != row["promoted_at"]


class TestConsumableSchemaV14Additions:
    """v1.4 §6 schema additions — field-ids 16, 17."""

    def test_endowment_value_provenance_field_id(self):
        schema = get_consumable_schema()
        f = next(f for f in schema.fields if f.name == "endowment_value_provenance")
        assert f.field_id == 16

    def test_endowment_value_provenance_is_nullable_string(self):
        """v1.4 §6: F3 rows are structurally NULL → must be nullable."""
        schema = get_consumable_schema()
        f = next(f for f in schema.fields if f.name == "endowment_value_provenance")
        assert isinstance(f.field_type, StringType)
        assert not f.required

    def test_source_load_date_field_id(self):
        schema = get_consumable_schema()
        f = next(f for f in schema.fields if f.name == "source_load_date")
        assert f.field_id == 17

    def test_source_load_date_is_required_date(self):
        """v1.4 §2 Decision G: NOT NULL preserves base's NOT NULL guarantee."""
        schema = get_consumable_schema()
        f = next(f for f in schema.fields if f.name == "source_load_date")
        assert isinstance(f.field_type, DateType)
        assert f.required


# ---------------------------------------------------------------------------
# v1.4 §6 — system-administrative-office filter (8 patterns AND-clause)
# ---------------------------------------------------------------------------


def _system_office_base_row(
    unitid: int,
    institution_name: str,
    instruction_expenses: float | None = 0.0,
    total_fte_enrollment: float | None = None,
) -> dict:
    """A base row that defaults to filtered-out — admin-pattern name +
    below-$1M instruction (or NULL) + FTE NULL.

    Callers can override ``instruction_expenses`` and
    ``total_fte_enrollment`` to exercise the v1.3 4-clause numeric proxy
    boundary cases.
    """
    return {
        "record_id": f"ipf-fake{unitid:08d}",
        "unitid": unitid,
        "institution_name": institution_name,
        "report_form": "F1A",
        "fiscal_year": 2023,
        "institutional_support_expenses": 5_000_000.0,
        "instruction_expenses": instruction_expenses,
        "endowment_value": None,
        "total_fte_enrollment": total_fte_enrollment,
        "institutional_support_per_fte": None,
        "instruction_per_fte": None,
        "endowment_per_fte": None,
        "marketing_ratio": None,
        "source_load_date": LOAD_DATE,
        "ingested_at": INGESTED_AT,
        "endowment_value_flag": "A",
    }


class TestSystemOfficeNamePatternMatch:
    """The 8 LIKE patterns translate to Python via
    ``_name_matches_system_office_pattern``.  Each pattern is testable in
    isolation."""

    @pytest.mark.parametrize(
        "name",
        [
            "U Colorado System Office",     # ends "% office" + contains "% system %"
            "Vermont State Colleges-Office of the Chancellor",  # "chancellor"
            "SUNY-System Office",           # "system office" + "% office"
            "Sistema Universitario Ana G. Mendez",  # spanish
            "LA CCD Office",                # ends "% office"
            "Big U System",                  # ends "% system"
            "Some Central Office Of Schools",  # "central office"
            "Foo District Office",           # "district office" + "% office"
        ],
    )
    def test_admin_pattern_names_match(self, name):
        assert _name_matches_system_office_pattern(name)

    @pytest.mark.parametrize(
        "name",
        [
            "Stanford University",
            "Massachusetts Institute of Technology",
            "Berea College",
            "Berklee College of Music",
            "Bay Area Community College",
            "University of California-Berkeley",
            "Sistema de Informacion School",  # "sistema" alone — not a system-office pattern
        ],
    )
    def test_real_school_names_dont_match(self, name):
        """Real teaching institutions whose names don't contain the 8
        admin-office anchored substrings must NOT match.  Note that the
        ``%sistema universitario%`` pattern is conservative — ``%sistema%``
        alone was rejected (§6 spec) to avoid Spanish-language
        false-positives."""
        assert not _name_matches_system_office_pattern(name)

    def test_none_name_does_not_match(self):
        """``institution_name=None`` doesn't blow up — returns False."""
        assert not _name_matches_system_office_pattern(None)

    def test_case_insensitive(self):
        """Matches SQL ``LOWER(institution_name)``."""
        assert _name_matches_system_office_pattern("LA CCD OFFICE")
        assert _name_matches_system_office_pattern("la ccd office")
        assert _name_matches_system_office_pattern("La Ccd Office")


class TestIsSystemOfficeRow:
    """The full filter predicate combines name pattern AND 4-clause
    numeric proxy — both halves must hold for exclusion (§2 Decision B).
    v1.3 amendment: the numeric proxy expanded from 2 to 4 disjuncts."""

    def test_admin_name_with_zero_instruction_excluded(self):
        row = _system_office_base_row(195827, "SUNY-System Office", instruction_expenses=0.0)
        assert is_system_office_row(row) is True

    def test_admin_name_with_null_instruction_excluded(self):
        row = _system_office_base_row(195827, "SUNY-System Office", instruction_expenses=None)
        assert is_system_office_row(row) is True

    def test_admin_name_with_500k_instruction_excluded(self):
        """$500K instruction < $1M floor → excluded."""
        row = _system_office_base_row(
            195827, "SUNY-System Office", instruction_expenses=500_000.0
        )
        assert is_system_office_row(row) is True

    def test_admin_name_with_999_999_instruction_excluded(self):
        """Boundary: just under $1M is still excluded."""
        row = _system_office_base_row(
            195827, "SUNY-System Office", instruction_expenses=999_999.99
        )
        assert is_system_office_row(row) is True

    def test_admin_name_with_1m_exact_and_positive_fte_preserved(self):
        """Boundary: exactly $1M instruction with positive FTE >= 50 is
        NOT below the floor on either disjunct → preserved."""
        row = _system_office_base_row(
            195827,
            "SUNY-System Office",
            instruction_expenses=1_000_000.0,
            total_fte_enrollment=500.0,
        )
        assert is_system_office_row(row) is False

    def test_admin_name_with_5m_instruction_and_positive_fte_preserved(self):
        """§2 Decision B AND-clause guardrail: a real school whose name
        matches a pattern but reports >= $1M instruction AND >= 50 FTE
        MUST SURVIVE."""
        row = _system_office_base_row(
            999100,
            "School of Office Systems",  # name matches "% office" / "% system %"
            instruction_expenses=5_000_000.0,
            total_fte_enrollment=2_000.0,
        )
        assert is_system_office_row(row) is False

    def test_real_school_name_with_low_instruction_preserved(self):
        """§2 Decision B AND-clause guardrail: a real teaching institution
        with sub-$1M instruction whose name does NOT match must be preserved.
        """
        row = _system_office_base_row(
            999200,
            "Tiny Berea-Style College",  # name doesn't match any of the 8 patterns
            instruction_expenses=400_000.0,
        )
        assert is_system_office_row(row) is False

    def test_sistema_universitario_excluded_with_null_instruction(self):
        """v1.1 §6: UNITID 242060 Sistema Universitario Ana G. Mendez —
        the live test target.  Spanish-language Puerto Rico system office
        with FTE NULL and (in real data) NULL instruction.  This row MUST
        be excluded by the 8th pattern."""
        row = _system_office_base_row(
            242060,
            "Sistema Universitario Ana G. Mendez",
            instruction_expenses=None,
        )
        assert is_system_office_row(row) is True

    def test_stanford_preserved(self):
        """Sanity: Stanford does not match any pattern and reports >> $1M
        instruction — must be preserved by the filter."""
        assert is_system_office_row(_stanford_base_row()) is False


class TestSystemOfficeFilterAtTransformRows:
    """Filter applied inside ``transform_rows`` — excluded rows never
    appear at consumable."""

    def test_filter_drops_excluded_rows(self):
        base = [
            _stanford_base_row(),  # preserved
            _system_office_base_row(195827, "SUNY-System Office", 0.0),  # excluded
            _system_office_base_row(128300, "U Colorado System Office", None),  # excluded
            _f3_base_row(199193),  # preserved
        ]
        consumable = transform_rows(base, promoted_at=PROMOTED_AT)
        unitids = {r["unitid"] for r in consumable}
        assert 243744 in unitids  # Stanford preserved
        assert 199193 in unitids  # F3 preserved
        assert 195827 not in unitids  # SUNY system office excluded
        assert 128300 not in unitids  # U Colorado system office excluded

    def test_sistema_universitario_242060_excluded(self):
        """Live test target per the spec §6 8th pattern."""
        base = [
            _stanford_base_row(),
            _system_office_base_row(
                242060, "Sistema Universitario Ana G. Mendez", None
            ),
        ]
        consumable = transform_rows(base, promoted_at=PROMOTED_AT)
        assert 242060 not in {r["unitid"] for r in consumable}
        assert 243744 in {r["unitid"] for r in consumable}

    def test_filter_preserves_admin_named_high_instruction(self):
        """A real school named "Office of Innovation" with $5M
        instruction AND positive FTE MUST survive (chaos pass §2
        Decision B; v1.3 4-clause proxy still preserves real schools)."""
        base = [
            _stanford_base_row(),
            _system_office_base_row(
                999300,
                "Office of Innovation in Teaching",
                5_000_000.0,
                total_fte_enrollment=2_500.0,
            ),
        ]
        consumable = transform_rows(base, promoted_at=PROMOTED_AT)
        assert 999300 in {r["unitid"] for r in consumable}

    def test_drop_does_not_affect_remaining_provenance(self):
        """Excluding a row must not perturb the remaining rows' fields."""
        base = [
            _stanford_base_row(),
            _system_office_base_row(195827, "SUNY-System Office", 0.0),
        ]
        consumable = transform_rows(base, promoted_at=PROMOTED_AT)
        assert len(consumable) == 1
        stanford = consumable[0]
        assert stanford["unitid"] == 243744
        assert stanford["endowment_value_provenance"] == "R"
        assert stanford["source_load_date"] == LOAD_DATE


class TestSystemOfficeFilterIntegration:
    """End-to-end base → consumable with filter exercise."""

    def test_filter_executes_at_promote(self, tmp_path):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        base = [
            _stanford_base_row(),
            _system_office_base_row(195827, "SUNY-System Office", 0.0),
            _system_office_base_row(128300, "U Colorado System Office", None),
            _system_office_base_row(
                242060, "Sistema Universitario Ana G. Mendez", None
            ),
            _f3_base_row(199193),
        ]
        project_dir = _seed_temp_base(tmp_path, base)
        result = transform(project_dir=project_dir, promoted_at=PROMOTED_AT)

        # 5 base rows in, 3 excluded, 2 in consumable.
        assert result["rows_read"] == 5
        assert result["rows_excluded_system_office"] == 3
        assert result["rows_transformed"] == 2
        assert result["promoted"] == 2
        assert set(result["excluded_unitids"]) == {195827, 128300, 242060}

        catalog = get_catalog(
            project_dir / "data" / "gold" / "iceberg_warehouse",
            project_dir / "data" / "catalog" / "catalog.db",
        )
        rows = read_with_duckdb(
            catalog.load_table(f"{CONSUMABLE_NAMESPACE}.{CONSUMABLE_TABLE_NAME}")
        )
        unitids = {r["unitid"] for r in rows}
        assert unitids == {243744, 199193}

    def test_provenance_passthrough_end_to_end(self, tmp_path):
        """CON-IFP-013 preview: provenance lands on every consumable row."""
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        base = [
            _stanford_base_row(),                  # R
            _f1a_a_provenance_base_row(100001),    # A
            _f2_n_provenance_base_row(100002),     # N
            _f3_base_row(199193),                  # NULL (F3 structural)
        ]
        project_dir = _seed_temp_base(tmp_path, base)
        transform(project_dir=project_dir, promoted_at=PROMOTED_AT)

        catalog = get_catalog(
            project_dir / "data" / "gold" / "iceberg_warehouse",
            project_dir / "data" / "catalog" / "catalog.db",
        )
        rows = read_with_duckdb(
            catalog.load_table(f"{CONSUMABLE_NAMESPACE}.{CONSUMABLE_TABLE_NAME}")
        )
        by_unitid = {r["unitid"]: r for r in rows}

        assert by_unitid[243744]["endowment_value_provenance"] == "R"
        assert by_unitid[100001]["endowment_value_provenance"] == "A"
        assert by_unitid[100002]["endowment_value_provenance"] == "N"
        assert by_unitid[199193]["endowment_value_provenance"] is None

    def test_source_load_date_100_percent_non_null(self, tmp_path):
        """CON-IFP-015 preview: every consumable row carries source_load_date."""
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        base = [
            _stanford_base_row(),
            _f1a_a_provenance_base_row(100001),
            _f3_base_row(199193),
        ]
        project_dir = _seed_temp_base(tmp_path, base)
        transform(project_dir=project_dir, promoted_at=PROMOTED_AT)

        catalog = get_catalog(
            project_dir / "data" / "gold" / "iceberg_warehouse",
            project_dir / "data" / "catalog" / "catalog.db",
        )
        rows = read_with_duckdb(
            catalog.load_table(f"{CONSUMABLE_NAMESPACE}.{CONSUMABLE_TABLE_NAME}")
        )
        assert all(r["source_load_date"] is not None for r in rows)
        assert len(rows) == 3


class TestSystemOfficeConstants:
    """Module constants exposed for the filter."""

    def test_eight_name_patterns(self):
        """v1.1 §6: eight patterns including the Spanish-language clause."""
        assert len(SYSTEM_OFFICE_NAME_PATTERNS) == 8

    def test_sistema_universitario_pattern_present(self):
        """v1.1 added ``%sistema universitario%`` for UNITID 242060."""
        assert "%sistema universitario%" in SYSTEM_OFFICE_NAME_PATTERNS

    def test_instruction_threshold_is_1m(self):
        assert SYSTEM_OFFICE_INSTRUCTION_THRESHOLD == 1_000_000.0

    def test_fte_threshold_is_50(self):
        """v1.3 amendment (chaos-monkey R1): FTE numeric-proxy threshold
        of 50 is well below any real teaching institution and catches
        the FTE-NULL admin cluster surfaced by the v1.4 chaos pass."""
        assert SYSTEM_OFFICE_FTE_THRESHOLD == 50.0


# ---------------------------------------------------------------------------
# v1.3 amendment (chaos-monkey R1) — FTE-disjunct extension to numeric proxy
# ---------------------------------------------------------------------------


# The 9 administrative entities surfaced by the v1.4 chaos pass: each
# has a name matching one of the 8 patterns, has `instruction_expenses`
# above $1M (in the $1.73M-$6.83M band), and has `total_fte_enrollment
# IS NULL`.  All 9 leaked past the v1.0–v1.2 2-clause numeric proxy and
# are caught by the v1.3 4-clause proxy via the FTE-NULL disjunct.
V13_NAMED_LEAKS: tuple[tuple[int, str, float], ...] = (
    (117681, "LA Community College District Office", 2_910_000.0),
    (195827, "SUNY-System Office", 2_213_252.0),
    (438665, "Rancho Santiago Community College District Office", 1_730_000.0),
    (222497, "Alamo Community College District Central Office", 4_500_000.0),
    (242671, "Inter American University of Puerto Rico-Central Office", 3_000_000.0),
    (166665, "University of Massachusetts-Central Office", 6_830_000.0),
    (454218, "Chamberlain University-Administrative Office", 5_200_000.0),
    (428453, "Minnesota State Colleges and Universities System Office", 3_400_000.0),
    (144777, "DeVry University-Administrative Office", 6_520_000.0),
)


class TestSystemOfficeFilterFTEExtensionV13:
    """v1.3 amendment (chaos-monkey R1): the 4-clause numeric proxy
    catches 9 administrative entities the 2-clause version missed.  All
    9 share the signature: name matches a pattern AND
    `instruction_expenses` >= $1M AND `total_fte_enrollment IS NULL`.
    Real teaching institutions have positive FTE; admin shells do not.
    """

    @pytest.mark.parametrize("unitid,name,instruction", V13_NAMED_LEAKS)
    def test_named_leak_excluded_by_fte_null_disjunct(
        self, unitid, name, instruction
    ):
        """Each of the 9 v1.4 chaos-pass-named leaks: instruction >= $1M
        with FTE NULL → caught by the v1.3 FTE-NULL disjunct.  Under the
        v1.0–v1.2 2-clause proxy these all survived (false-negatives).
        """
        row = _system_office_base_row(
            unitid,
            name,
            instruction_expenses=instruction,
            total_fte_enrollment=None,
        )
        assert is_system_office_row(row) is True

    def test_admin_name_high_instruction_with_real_fte_preserved(self):
        """Symmetric false-positive guard: a row with an admin-pattern
        name and `instruction >= $1M` but `total_fte_enrollment >= 50`
        SURVIVES (real teaching institution case — must not be excluded
        by the FTE disjuncts)."""
        row = _system_office_base_row(
            999500,
            "School of Office Studies",  # matches "% office" / "% system %"
            instruction_expenses=5_000_000.0,
            total_fte_enrollment=500.0,
        )
        assert is_system_office_row(row) is False

    def test_fte_50_exact_with_high_instruction_preserved(self):
        """Boundary (`< 50` is strict less-than): FTE = 50 exactly does
        NOT trigger the FTE-low disjunct.  With instruction >= $1M, the
        row survives."""
        row = _system_office_base_row(
            999501,
            "Foo District Office",
            instruction_expenses=2_000_000.0,
            total_fte_enrollment=50.0,
        )
        assert is_system_office_row(row) is False

    def test_fte_49_with_high_instruction_excluded(self):
        """Boundary (`< 50` is strict less-than): FTE = 49 triggers the
        FTE-low disjunct.  With an admin-pattern name, the row is
        excluded even when instruction is well above $1M."""
        row = _system_office_base_row(
            999502,
            "Foo District Office",
            instruction_expenses=2_000_000.0,
            total_fte_enrollment=49.0,
        )
        assert is_system_office_row(row) is True

    def test_instruction_1m_exact_with_null_fte_excluded(self):
        """Boundary (`< 1_000_000.0` is strict less-than): instruction
        = exactly $1M does not trigger the instruction-low disjunct,
        but with FTE NULL the FTE-NULL disjunct fires → excluded."""
        row = _system_office_base_row(
            999503,
            "SUNY-System Office",
            instruction_expenses=1_000_000.0,
            total_fte_enrollment=None,
        )
        assert is_system_office_row(row) is True

    def test_instruction_999_999_with_high_fte_excluded(self):
        """Boundary: instruction = $999,999 < $1M triggers the
        instruction-low disjunct.  Even with positive FTE >= 50 the row
        is excluded — only ONE of the four disjuncts needs to fire when
        the name pattern matches."""
        row = _system_office_base_row(
            999504,
            "SUNY-System Office",
            instruction_expenses=999_999.0,
            total_fte_enrollment=200.0,
        )
        assert is_system_office_row(row) is True

    def test_named_leaks_excluded_at_transform_rows(self):
        """End-to-end at `transform_rows`: all 9 v1.3-caught named leaks
        are dropped before promote, none appear in the consumable
        output."""
        base = [_stanford_base_row()]
        for unitid, name, instruction in V13_NAMED_LEAKS:
            base.append(
                _system_office_base_row(
                    unitid,
                    name,
                    instruction_expenses=instruction,
                    total_fte_enrollment=None,
                )
            )
        consumable = transform_rows(base, promoted_at=PROMOTED_AT)
        unitids = {r["unitid"] for r in consumable}
        assert 243744 in unitids  # Stanford preserved
        for unitid, _, _ in V13_NAMED_LEAKS:
            assert unitid not in unitids, (
                f"v1.3 named leak UNITID {unitid} should be excluded but survived"
            )

    def test_v12_2clause_baseline_still_excluded(self):
        """Regression guard: the v1.0–v1.2 2-clause proxy cases (admin
        name + instruction NULL or < $1M) MUST still be excluded under
        the v1.3 4-clause proxy.  v1.3 is additive — it strengthens
        exclusion, never relaxes it."""
        # Admin name + zero instruction + FTE positive: still excluded
        # via the instruction-zero (< $1M) disjunct.
        row = _system_office_base_row(
            999600,
            "SUNY-System Office",
            instruction_expenses=0.0,
            total_fte_enrollment=500.0,
        )
        assert is_system_office_row(row) is True

    def test_real_small_teaching_school_with_admin_pattern_name_preserved(self):
        """v1.3 false-positive shield: a hypothetical small teaching
        institution whose legal name happens to contain "Office" but
        which has positive FTE >= 50 and instruction >= $1M MUST
        survive.  Real teaching institutions cannot operate without
        students; the FTE disjunct is the structural guardrail."""
        row = _system_office_base_row(
            999700,
            "Berea Office College",  # contrived name matching "% office"
            instruction_expenses=3_500_000.0,
            total_fte_enrollment=1_200.0,
        )
        assert is_system_office_row(row) is False
