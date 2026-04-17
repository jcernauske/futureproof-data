"""Tests for src/raw/gemma_ai_exposure_ingestor.GemmaAiExposureIngestor."""

import datetime
import json
from unittest.mock import MagicMock

import pytest

from raw.gemma_ai_exposure_ingestor import GemmaAiExposureIngestor


def _make_ingestor():
    ingestor = GemmaAiExposureIngestor.__new__(GemmaAiExposureIngestor)
    ingestor.source = MagicMock()
    ingestor.manifest = MagicMock()
    return ingestor


SAMPLE_PAYLOAD = [
    {
        "soc_code": "13-2051",
        "primary_title": "Financial Analysts",
        "exposure_score": 7,
        "rationale": "Financial analysts process data and build models.",
        "task_breakdown_automatable": '["Data aggregation"]',
        "task_breakdown_human": '["Client relationships"]',
        "scoring_model": "gemma-4",
        "model_tag": "gemma4:26b-a4b",
        "scored_at": "2026-04-16T12:00:00+00:00",
        "error": None,
    },
    {
        # Error row — should still be promoted to Bronze for audit.
        "soc_code": "99-9999",
        "primary_title": None,
        "error": "Failed after 3 attempts: invalid JSON",
        "raw_response": "not json at all",
        "scoring_model": "gemma-4",
        "model_tag": "gemma4:26b-a4b",
        "scored_at": "2026-04-16T12:05:00+00:00",
    },
]


def test_fetch_loads_fixture_and_echoes_per_entity(tmp_path):
    """fetch() reads the JSON fixture and echoes the payload per entity."""
    fixture = tmp_path / "gemma-ai-exposure-scores.json"
    fixture.write_text(json.dumps(SAMPLE_PAYLOAD))

    ingestor = _make_ingestor()
    result = ingestor.fetch(
        entities={"gemma_ai_exposure": "Gemma AI Exposure"},
        method="fixture_file",
        fixture_path=str(fixture),
    )

    assert "gemma_ai_exposure" in result
    assert result["gemma_ai_exposure"]["scores"] == SAMPLE_PAYLOAD


def test_fetch_missing_fixture_raises():
    ingestor = _make_ingestor()
    with pytest.raises(FileNotFoundError):
        ingestor.fetch(
            entities={"x": "x"},
            method="fixture_file",
            fixture_path="/nonexistent/path.json",
        )


def test_flatten_produces_one_row_per_entry():
    ingestor = _make_ingestor()
    rows = ingestor.flatten(
        {"scores": SAMPLE_PAYLOAD, "source_path": "test"},
        entity_id="gemma_ai_exposure",
    )
    assert len(rows) == 2

    # Successful row
    success = rows[0]
    assert success["bls_soc_code"] == "13-2051"
    assert success["exposure_score"] == 7
    assert success["scoring_model"] == "gemma-4"
    assert success["model_tag"] == "gemma4:26b-a4b"
    assert success["error"] is None
    assert isinstance(success["scored_at"], datetime.datetime)

    # Error row — preserved for audit
    err = rows[1]
    assert err["bls_soc_code"] == "99-9999"
    assert err["error"] == "Failed after 3 attempts: invalid JSON"
    assert err["raw_response"] == "not json at all"
    assert err["exposure_score"] is None


def test_flatten_skips_entries_without_soc():
    ingestor = _make_ingestor()
    rows = ingestor.flatten(
        {"scores": [{"primary_title": "no soc", "exposure_score": 5}]},
        entity_id="x",
    )
    assert rows == []


def test_get_schema_has_required_fields():
    ingestor = _make_ingestor()
    schema = ingestor.get_schema()
    names = [f.name for f in schema.fields]
    # Spot-check a few critical fields.
    assert "bls_soc_code" in names
    assert "model_tag" in names
    assert "error" in names
    assert "scoring_model" in names
    # Ingested metadata is framework-added.
    assert "ingested_at" in names
    assert "source_url" in names

    # bls_soc_code is the only required data-level column (at Bronze
    # errors are allowed to omit other fields).
    by_name = {f.name: f for f in schema.fields}
    assert by_name["bls_soc_code"].required
    assert by_name["scoring_model"].required
    assert not by_name["exposure_score"].required
