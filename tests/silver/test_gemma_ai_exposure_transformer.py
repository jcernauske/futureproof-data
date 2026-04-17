"""Tests for src/silver/gemma_ai_exposure_transformer.transform_rows."""

import datetime

from silver.gemma_ai_exposure_transformer import (
    normalize_soc,
    transform_rows,
)


def _bronze_row(
    soc="13-2051",
    title="Financial Analysts",
    exposure=7,
    rationale="rationale " * 20,
    model_tag="gemma4:26b-a4b",
    error=None,
):
    return {
        "bls_soc_code": soc,
        "primary_title": title,
        "exposure_score": exposure,
        "rationale": rationale,
        "task_breakdown_automatable": '["x"]',
        "task_breakdown_human": '["y"]',
        "scoring_model": "gemma-4",
        "model_tag": model_tag,
        "scored_at": datetime.datetime.now(tz=datetime.timezone.utc),
        "error": error,
    }


class TestNormalizeSoc:
    def test_valid_format_passthrough(self):
        assert normalize_soc("13-2051") == "13-2051"

    def test_strips_whitespace(self):
        assert normalize_soc("  13-2051 ") == "13-2051"

    def test_six_digits_without_hyphen(self):
        assert normalize_soc("132051") == "13-2051"

    def test_none_and_empty_return_none(self):
        assert normalize_soc(None) is None
        assert normalize_soc("") is None
        assert normalize_soc("   ") is None

    def test_unrecognized_returns_none(self):
        assert normalize_soc("not a soc") is None
        assert normalize_soc("12-34") is None  # too short


class TestTransformRows:
    def test_drops_error_rows(self):
        rows = [
            _bronze_row(soc="13-2051"),
            _bronze_row(soc="15-1252", error="parse failure"),
        ]
        silver = transform_rows(rows, onet_soc_set={"13-2051", "15-1252"})
        assert len(silver) == 1
        assert silver[0]["soc_code_normalized"] == "13-2051"

    def test_drops_unnormalizable_soc(self):
        rows = [_bronze_row(soc="not a soc")]
        silver = transform_rows(rows, onet_soc_set=set())
        assert silver == []

    def test_drops_duplicate_socs(self):
        rows = [
            _bronze_row(soc="13-2051", exposure=7),
            _bronze_row(soc="13-2051", exposure=8),
        ]
        silver = transform_rows(rows, onet_soc_set={"13-2051"})
        assert len(silver) == 1
        # First-seen wins.
        assert silver[0]["exposure_score"] == 7

    def test_join_valid_flag(self):
        rows = [
            _bronze_row(soc="13-2051"),
            _bronze_row(soc="99-9999"),
        ]
        silver = transform_rows(rows, onet_soc_set={"13-2051"})
        by_soc = {r["soc_code_normalized"]: r for r in silver}
        assert by_soc["13-2051"]["join_valid"] is True
        assert by_soc["99-9999"]["join_valid"] is False

    def test_every_row_has_record_id_with_gae_prefix(self):
        rows = [_bronze_row(soc="13-2051")]
        silver = transform_rows(rows, onet_soc_set={"13-2051"})
        assert silver[0]["record_id"].startswith("gae-")

    def test_drops_rows_with_missing_required_fields(self):
        """Bronze rows without exposure_score or rationale are dropped."""
        rows = [
            _bronze_row(soc="13-2051", exposure=None),
            _bronze_row(soc="15-1252", rationale=None),
        ]
        silver = transform_rows(rows, onet_soc_set={"13-2051", "15-1252"})
        assert silver == []

    def test_preserves_model_tag_for_reproducibility(self):
        rows = [_bronze_row(soc="13-2051", model_tag="gemma4:26b-a4b")]
        silver = transform_rows(rows, onet_soc_set={"13-2051"})
        assert silver[0]["model_tag"] == "gemma4:26b-a4b"
