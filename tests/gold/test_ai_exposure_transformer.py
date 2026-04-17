"""Tests for the Gold zone AI exposure transformer.

Covers stat_res derivation (all edge cases), boss_ai_score derivation,
bls_match filtering, null SOC handling, record ID computation, schema
validation, cross-field invariant, and end-to-end derive_gold_rows.
"""

import datetime

from gold.ai_exposure_transformer import (
    add_record_ids,
    compute_boss_ai_score,
    compute_stat_res,
    derive_gold_rows,
    get_gold_schema,
)
from brightsmith.infra.grain import compute_grain_id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_silver_row(
    soc_code="13-2051",
    slug="financial-analysts",
    occupation_title="Financial analysts",
    category="business-and-financial",
    exposure_score=8,
    rationale="Financial analysts work almost entirely on computers, processing data.",
    bls_match=True,
    soc_resolved_method="direct",
    source_load_date=datetime.date(2026, 4, 9),
    ingested_at=datetime.datetime(2026, 4, 9, 0, 0, 0),
    record_id="kai-abc123",
):
    """Build a Silver-shaped row for testing (matches base.karpathy_ai_exposure schema)."""
    return {
        "record_id": record_id,
        "soc_code": soc_code,
        "slug": slug,
        "occupation_title": occupation_title,
        "category": category,
        "exposure_score": exposure_score,
        "rationale": rationale,
        "bls_match": bls_match,
        "soc_resolved_method": soc_resolved_method,
        "source_load_date": source_load_date,
        "ingested_at": ingested_at,
    }


# ---------------------------------------------------------------------------
# stat_res derivation
# ---------------------------------------------------------------------------

class TestComputeStatRes:
    """Tests for the stat_res = MIN(11 - exposure_score, 10) derivation."""

    def test_exposure_0_caps_at_10(self):
        """exposure_score=0 -> 11-0=11, capped at 10."""
        assert compute_stat_res(0) == 10

    def test_exposure_1_equals_10(self):
        """exposure_score=1 -> 11-1=10, no cap needed."""
        assert compute_stat_res(1) == 10

    def test_exposure_5_moderate(self):
        """exposure_score=5 -> stat_res=6."""
        assert compute_stat_res(5) == 6

    def test_exposure_7_high(self):
        """exposure_score=7 -> stat_res=4."""
        assert compute_stat_res(7) == 4

    def test_exposure_9_very_high(self):
        """exposure_score=9 -> stat_res=2."""
        assert compute_stat_res(9) == 2

    def test_exposure_10_maximum(self):
        """exposure_score=10 -> stat_res=1 (minimal resilience)."""
        assert compute_stat_res(10) == 1

    def test_all_valid_scores_in_range(self):
        """All exposure scores 0-10 produce stat_res in [1, 10]."""
        for score in range(11):
            result = compute_stat_res(score)
            assert 1 <= result <= 10, f"exposure={score} -> stat_res={result} out of range"


# ---------------------------------------------------------------------------
# boss_ai_score derivation
# ---------------------------------------------------------------------------

class TestComputeBossAiScore:
    """Tests for the boss_ai_score = MAX(exposure_score, 1) derivation."""

    def test_exposure_0_floors_at_1(self):
        """exposure_score=0 -> boss_ai_score=1 (every boss has min strength 1)."""
        assert compute_boss_ai_score(0) == 1

    def test_exposure_1_equals_1(self):
        """exposure_score=1 -> boss_ai_score=1."""
        assert compute_boss_ai_score(1) == 1

    def test_exposure_5_direct(self):
        """exposure_score=5 -> boss_ai_score=5."""
        assert compute_boss_ai_score(5) == 5

    def test_exposure_10_direct(self):
        """exposure_score=10 -> boss_ai_score=10."""
        assert compute_boss_ai_score(10) == 10

    def test_all_valid_scores_in_range(self):
        """All exposure scores 0-10 produce boss_ai_score in [1, 10]."""
        for score in range(11):
            result = compute_boss_ai_score(score)
            assert 1 <= result <= 10, f"exposure={score} -> boss={result} out of range"


# ---------------------------------------------------------------------------
# Cross-field invariant: stat_res + boss_ai_score = 11
# ---------------------------------------------------------------------------

class TestCrossFieldInvariant:
    """For exposure_score >= 1, stat_res + boss_ai_score must equal 11."""

    def test_invariant_holds_for_scores_1_through_10(self):
        for score in range(1, 11):
            stat = compute_stat_res(score)
            boss = compute_boss_ai_score(score)
            assert stat + boss == 11, (
                f"exposure={score}: stat_res={stat} + boss_ai={boss} = {stat + boss}, expected 11"
            )

    def test_invariant_holds_for_exposure_0(self):
        """Special case: exposure=0 -> stat_res=10, boss=1, sum=11."""
        assert compute_stat_res(0) + compute_boss_ai_score(0) == 11


# ---------------------------------------------------------------------------
# derive_gold_rows
# ---------------------------------------------------------------------------

class TestDeriveGoldRows:
    """Tests for the full derive_gold_rows pipeline."""

    def test_filters_bls_match_false(self):
        """Rows with bls_match=false are excluded."""
        rows = [
            _make_silver_row(soc_code="13-2051", bls_match=True),
            _make_silver_row(soc_code="99-9999", bls_match=False),
        ]
        gold = derive_gold_rows(rows)
        assert len(gold) == 1
        assert gold[0]["soc_code"] == "13-2051"

    def test_filters_null_soc(self):
        """Rows with null soc_code are excluded even if bls_match=true."""
        rows = [_make_silver_row(soc_code=None, bls_match=True)]
        gold = derive_gold_rows(rows)
        assert len(gold) == 0

    def test_carries_forward_fields(self):
        """Gold rows carry forward soc_code, occupation_title, exposure_score, rationale, category."""
        rows = [_make_silver_row(
            soc_code="15-1252",
            occupation_title="Software Developers",
            exposure_score=7,
            rationale="They code all day.",
            category="computer-and-mathematical",
        )]
        gold = derive_gold_rows(rows)
        assert len(gold) == 1
        r = gold[0]
        assert r["soc_code"] == "15-1252"
        assert r["occupation_title"] == "Software Developers"
        assert r["exposure_score"] == 7
        assert r["rationale"] == "They code all day."
        assert r["category"] == "computer-and-mathematical"

    def test_drops_silver_only_fields(self):
        """Gold rows should not contain slug, bls_match, soc_resolved_method, etc."""
        rows = [_make_silver_row()]
        gold = derive_gold_rows(rows)
        r = gold[0]
        assert "slug" not in r
        assert "bls_match" not in r
        assert "soc_resolved_method" not in r
        assert "source_load_date" not in r
        assert "ingested_at" not in r

    def test_derives_stat_res_and_boss(self):
        """Gold rows have correct stat_res and boss_ai_score derived."""
        rows = [_make_silver_row(exposure_score=8)]
        gold = derive_gold_rows(rows)
        r = gold[0]
        assert r["stat_res"] == 3  # 11 - 8 = 3
        assert r["boss_ai_score"] == 8  # max(8, 1) = 8

    def test_empty_input(self):
        """Empty Silver rows produce empty Gold rows."""
        assert derive_gold_rows([]) == []

    def test_all_filtered_out(self):
        """If all rows have bls_match=false, result is empty."""
        rows = [
            _make_silver_row(soc_code="11-1011", bls_match=False),
            _make_silver_row(soc_code="11-1021", bls_match=False),
        ]
        assert derive_gold_rows(rows) == []

    def test_multiple_rows_preserve_order(self):
        """Multiple matching rows are returned in input order."""
        rows = [
            _make_silver_row(soc_code="11-1011", exposure_score=3),
            _make_silver_row(soc_code="15-1252", exposure_score=7),
            _make_silver_row(soc_code="29-1141", exposure_score=2),
        ]
        gold = derive_gold_rows(rows)
        assert len(gold) == 3
        assert [r["soc_code"] for r in gold] == ["11-1011", "15-1252", "29-1141"]


# ---------------------------------------------------------------------------
# add_record_ids
# ---------------------------------------------------------------------------

class TestAddRecordIds:
    """Tests for record ID computation and promoted_at assignment."""

    def test_adds_record_id(self):
        """record_id is computed with 'aie' prefix from soc_code grain."""
        gold_rows = [{"soc_code": "13-2051", "occupation_title": "Financial analysts"}]
        promoted_at = datetime.datetime(2026, 4, 9, 12, 0, 0, tzinfo=datetime.timezone.utc)
        add_record_ids(gold_rows, promoted_at)

        expected_id = compute_grain_id({"soc_code": "13-2051"}, ["soc_code"], prefix="aie")
        assert gold_rows[0]["record_id"] == expected_id
        assert gold_rows[0]["record_id"].startswith("aie-")

    def test_adds_promoted_at(self):
        """promoted_at is set to the given timestamp."""
        gold_rows = [{"soc_code": "13-2051"}]
        ts = datetime.datetime(2026, 4, 9, 12, 0, 0, tzinfo=datetime.timezone.utc)
        add_record_ids(gold_rows, ts)
        assert gold_rows[0]["promoted_at"] == ts

    def test_deterministic_ids(self):
        """Same soc_code always produces the same record_id."""
        rows_a = [{"soc_code": "15-1252"}]
        rows_b = [{"soc_code": "15-1252"}]
        ts = datetime.datetime(2026, 4, 9, 0, 0, 0, tzinfo=datetime.timezone.utc)
        add_record_ids(rows_a, ts)
        add_record_ids(rows_b, ts)
        assert rows_a[0]["record_id"] == rows_b[0]["record_id"]

    def test_different_soc_different_ids(self):
        """Different soc_codes produce different record_ids."""
        rows = [{"soc_code": "13-2051"}, {"soc_code": "15-1252"}]
        ts = datetime.datetime(2026, 4, 9, 0, 0, 0, tzinfo=datetime.timezone.utc)
        add_record_ids(rows, ts)
        assert rows[0]["record_id"] != rows[1]["record_id"]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestGoldSchema:
    """Tests for the Iceberg schema definition.

    S3 extends the schema to 18 fields: original 9 + 5 v4 additive
    (Gemma/Karpathy blending) + 4 S3 additive (Anthropic observed
    exposure).
    """

    def test_schema_has_23_fields(self):
        """S4 v4 schema has 23 columns: 9 original + 5 Gemma + 4 Anthropic + 5 composite."""
        schema = get_gold_schema()
        assert len(schema.fields) == 23

    def test_schema_field_names(self):
        """All expected field names are present in the documented order."""
        schema = get_gold_schema()
        names = [f.name for f in schema.fields]
        expected = [
            # Original 9 (preserved for backward compatibility)
            "record_id", "soc_code", "occupation_title", "exposure_score",
            "stat_res", "boss_ai_score", "rationale", "category", "promoted_at",
            # v4 additive (Gemma/Karpathy blending)
            "task_breakdown_automatable", "task_breakdown_human",
            "scoring_model", "model_tag", "karpathy_score",
            # Anthropic Economic Index passthrough (field 15 renamed v4)
            "ai_adoption_share", "automation_pct",
            "anthropic_task_count", "anthropic_source_release",
            # S4 v4 Option B composite fields
            "composite_exposure", "adoption_percentile", "confidence_weight",
            "velocity_label", "composite_method",
        ]
        assert names == expected

    def test_original_fields_required(self):
        """The original 9 fields remain NOT NULL per physical model."""
        schema = get_gold_schema()
        required_fields = {
            "record_id", "soc_code", "occupation_title", "exposure_score",
            "stat_res", "boss_ai_score", "rationale", "category", "promoted_at",
        }
        for field in schema.fields:
            if field.name in required_fields:
                assert field.required, f"Original field {field.name} must be required"

    def test_scoring_model_required(self):
        """scoring_model is required at Gold (always 'gemma-4' or 'gemini-flash')."""
        schema = get_gold_schema()
        by_name = {f.name: f for f in schema.fields}
        assert by_name["scoring_model"].required

    def test_optional_v4_fields(self):
        """task_breakdown_*, model_tag, karpathy_score are nullable by design."""
        schema = get_gold_schema()
        by_name = {f.name: f for f in schema.fields}
        for fname in (
            "task_breakdown_automatable",
            "task_breakdown_human",
            "model_tag",
            "karpathy_score",
        ):
            assert not by_name[fname].required, (
                f"v4 additive field {fname} should be nullable"
            )


# ---------------------------------------------------------------------------
# End-to-end derive + record IDs
# ---------------------------------------------------------------------------

class TestEndToEnd:
    """End-to-end test combining derive_gold_rows and add_record_ids."""

    def test_full_pipeline(self):
        """Silver input -> Gold output with all fields populated."""
        silver = [
            _make_silver_row(soc_code="13-2051", exposure_score=8, bls_match=True),
            _make_silver_row(soc_code="29-1141", exposure_score=2, bls_match=True),
            _make_silver_row(soc_code="99-9999", exposure_score=5, bls_match=False),
        ]
        gold = derive_gold_rows(silver)
        assert len(gold) == 2

        ts = datetime.datetime(2026, 4, 9, 12, 0, 0, tzinfo=datetime.timezone.utc)
        add_record_ids(gold, ts)

        # Verify first row
        r = gold[0]
        assert r["soc_code"] == "13-2051"
        assert r["exposure_score"] == 8
        assert r["stat_res"] == 3
        assert r["boss_ai_score"] == 8
        assert r["record_id"].startswith("aie-")
        assert r["promoted_at"] == ts

        # Verify second row
        r2 = gold[1]
        assert r2["soc_code"] == "29-1141"
        assert r2["stat_res"] == 9  # 11 - 2 = 9
        assert r2["boss_ai_score"] == 2

    def test_gold_row_has_v4_field_set(self):
        """Karpathy-only path stamps v4 + S3 additive fields with None/flash provenance."""
        silver = [_make_silver_row(exposure_score=5)]
        gold = derive_gold_rows(silver)
        ts = datetime.datetime(2026, 4, 9, 0, 0, 0, tzinfo=datetime.timezone.utc)
        add_record_ids(gold, ts)

        # S4 v4 schema = original 9 + 5 v4 + 4 Anthropic + 5 composite fields.
        expected_keys = {
            "record_id", "soc_code", "occupation_title", "exposure_score",
            "stat_res", "boss_ai_score", "rationale", "category", "promoted_at",
            "task_breakdown_automatable", "task_breakdown_human",
            "scoring_model", "model_tag", "karpathy_score",
            "ai_adoption_share", "automation_pct",
            "anthropic_task_count", "anthropic_source_release",
            "composite_exposure", "adoption_percentile", "confidence_weight",
            "velocity_label", "composite_method",
        }
        assert set(gold[0].keys()) == expected_keys

        # Karpathy-only path stamps gemini-flash provenance.
        r = gold[0]
        assert r["scoring_model"] == "gemini-flash"
        assert r["model_tag"] is None
        assert r["task_breakdown_automatable"] is None
        assert r["task_breakdown_human"] is None
        assert r["karpathy_score"] == 5  # equal to exposure_score

        # Karpathy-only fallback has no Anthropic bridge — all four
        # Anthropic columns emit None. The full transform() path
        # injects real values via blend_scores + _index_anthropic.
        assert r["ai_adoption_share"] is None
        assert r["automation_pct"] is None
        assert r["anthropic_task_count"] is None
        assert r["anthropic_source_release"] is None

        # Composite fields: karpathy-only path stamps karpathy_only method
        # + unknown velocity + neutral 0.5 confidence; composite_exposure
        # mirrors the raw Karpathy score.
        assert r["composite_method"] == "karpathy_only"
        assert r["velocity_label"] == "unknown"
        assert r["confidence_weight"] == 0.5
        assert r["adoption_percentile"] is None
        assert r["composite_exposure"] == 5
