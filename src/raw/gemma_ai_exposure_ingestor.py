"""Ingestor for Gemma 4 AI Exposure Scores.

Reads the committed batch-scoring artifact at
``governance/fixtures/gemma-ai-exposure-scores.json`` — one row per
O*NET occupation (~798), produced by ``scripts/gemma_ai_exposure_scorer.py``
— and appends to the Bronze zone as ``raw.gemma_ai_exposure``.

Grain: bls_soc_code (one row per occupation).

The scorer writes both successful scores and error rows. Both are
promoted to Bronze; the Silver transformer filters out ``error != NULL``
rows before dedup. Row-level ``model_tag`` preserves the exact Ollama
model version for audit reproducibility.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.bronze.base_ingestor import BaseIngestor

logger = logging.getLogger(__name__)


class GemmaAiExposureIngestor(BaseIngestor):
    """Ingest Gemma 4 AI exposure scores from the committed fixture file.

    Data source: single JSON file at ``governance/fixtures/``.  Each
    element is one occupation's score, following the shape produced by
    ``scripts/gemma_ai_exposure_scorer.score_occupation``::

        {
          "soc_code": "13-2051",
          "primary_title": "Financial Analysts",
          "exposure_score": 7,
          "rationale": "...",
          "task_breakdown_automatable": "[\"...\"]",
          "task_breakdown_human": "[\"...\"]",
          "scoring_model": "gemma-4",
          "model_tag": "gemma4:26b-a4b",
          "scored_at": "2026-04-16T12:00:00+00:00",
          "error": null
        }

    Error rows preserve ``error`` and ``raw_response`` so Silver DQ can
    measure the failure rate and the debugger can inspect Gemma's
    malformed output.
    """

    FIXTURE_PATH = "governance/fixtures/gemma-ai-exposure-scores.json"

    def fetch(self, entities: dict, method: str, **kwargs: Any) -> dict:
        """Load the committed JSON artifact.

        Args:
            entities: ``{entity_id: label}`` from source config.
            method: Fetch method name (only ``"fixture_file"`` supported).
            **kwargs: Supports ``fixture_path`` for test-mode override.

        Returns:
            ``{entity_id: payload_dict}`` — same payload echoed for every
            entity so downstream ``flatten`` sees it once per entity.
        """
        fixture_path = kwargs.get("fixture_path") or self.FIXTURE_PATH
        path = Path(fixture_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            raise FileNotFoundError(
                f"Gemma scores fixture not found at {path}. Run "
                f"scripts/gemma_ai_exposure_scorer.py to produce it."
            )

        with open(path) as f:
            scores = json.load(f)

        if not isinstance(scores, list):
            raise ValueError(
                f"Expected a JSON list at {path}; got {type(scores).__name__}"
            )

        logger.info("Loaded %d Gemma score rows from %s", len(scores), path)
        payload = {"scores": scores, "source_path": str(path)}
        return {entity_id: payload for entity_id in entities}

    def flatten(self, raw_data: Any, entity_id: Any) -> list[dict]:
        """Flatten the scorer JSON into one Bronze row per occupation."""
        scores = raw_data["scores"]
        rows: list[dict] = []

        for entry in scores:
            soc = self._coerce_string(entry.get("soc_code"))
            if not soc:
                logger.warning(
                    "Skipping Gemma score with missing soc_code: %s",
                    str(entry)[:200],
                )
                continue

            rows.append({
                "bls_soc_code": soc,
                "primary_title": self._coerce_string(entry.get("primary_title")),
                "exposure_score": self._coerce_int(entry.get("exposure_score")),
                "rationale": self._coerce_string(entry.get("rationale")),
                "task_breakdown_automatable": self._coerce_string(
                    entry.get("task_breakdown_automatable")
                ),
                "task_breakdown_human": self._coerce_string(
                    entry.get("task_breakdown_human")
                ),
                "scoring_model": self._coerce_string(
                    entry.get("scoring_model")
                ) or "gemma-4",
                "model_tag": self._coerce_string(entry.get("model_tag")),
                "scored_at": self._coerce_timestamp(entry.get("scored_at")),
                "error": self._coerce_string(entry.get("error")),
                "raw_response": self._coerce_string(entry.get("raw_response")),
            })

        logger.info("Flattened %d Gemma score rows", len(rows))
        return rows

    def get_source_url(self, entity_id: Any, method: str) -> str:
        """Return the source path for lineage purposes."""
        return f"file://{self.FIXTURE_PATH}"

    def get_schema(self) -> Schema:
        """Iceberg schema for bronze.raw_gemma_ai_exposure."""
        return Schema(
            # Grain
            NestedField(1, "bls_soc_code", StringType(), required=True),
            # Core data
            NestedField(2, "primary_title", StringType(), required=False),
            NestedField(3, "exposure_score", IntegerType(), required=False),
            NestedField(4, "rationale", StringType(), required=False),
            # Task breakdown (JSON-encoded arrays)
            NestedField(5, "task_breakdown_automatable", StringType(), required=False),
            NestedField(6, "task_breakdown_human", StringType(), required=False),
            # Provenance + reproducibility
            NestedField(7, "scoring_model", StringType(), required=True),
            NestedField(8, "model_tag", StringType(), required=False),
            NestedField(9, "scored_at", TimestampType(), required=False),
            # Error-row fields (null for successful scores)
            NestedField(10, "error", StringType(), required=False),
            NestedField(11, "raw_response", StringType(), required=False),
            # Framework metadata
            NestedField(12, "ingested_at", TimestampType(), required=True),
            NestedField(13, "source_url", StringType(), required=True),
            NestedField(14, "source_method", StringType(), required=True),
            NestedField(15, "load_date", DateType(), required=True),
        )

    # ------------------------------------------------------------------
    # Coercion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_string(value: Any) -> str | None:
        """Coerce to string or None."""
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        """Coerce to int or None. Accepts numeric strings."""
        if value is None:
            return None
        if isinstance(value, bool):
            # bool is a subclass of int — reject explicitly.
            return None
        if isinstance(value, int):
            return value
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _coerce_timestamp(value: Any):
        """Coerce ISO-8601 string to datetime, pass through datetimes."""
        import datetime as _dt

        if value is None:
            return None
        if isinstance(value, _dt.datetime):
            return value
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None
            try:
                # Python 3.11+ fromisoformat supports trailing Z via
                # replace, but be defensive for older scorer outputs.
                return _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
#
# Loads the gemma_ai_exposure source from domain/manifest.yaml and runs
# the BaseIngestor pipeline (fetch -> flatten -> dedup -> append).
# Invoked as: ``uv run python src/raw/gemma_ai_exposure_ingestor.py``


def _run_cli() -> dict:
    """Load source config from the domain manifest and run ingest."""
    from brightsmith.domain_loader import (
        DEFAULT_MANIFEST_PATH,
        SourceConfig,
    )
    import yaml

    manifest = yaml.safe_load(DEFAULT_MANIFEST_PATH.read_text())
    source_entry = next(
        (s for s in manifest.get("sources", [])
         if s.get("name") == "gemma_ai_exposure"),
        None,
    )
    if source_entry is None:
        raise RuntimeError(
            "gemma_ai_exposure source not found in domain/manifest.yaml. "
            "Add it before running the ingestor."
        )

    repo_root = DEFAULT_MANIFEST_PATH.parent.parent
    source_path = repo_root / source_entry["source_config"]
    source_yaml = yaml.safe_load(source_path.read_text())

    source = SourceConfig(
        name=source_yaml["name"],
        namespace=source_yaml["namespace"],
        table=source_yaml["table"],
        fetch=source_yaml.get("fetch") or {},
        entities=source_yaml.get("entities") or {},
        dedup_grain=source_yaml.get("dedup_grain") or [],
        cache_dir=source_yaml.get("cache_dir") or "governance/fixtures",
    )

    # DomainManifest is constructed lazily by the framework via its own
    # loader; for a one-off ingest we only need the SourceConfig and a
    # minimal stand-in for `manifest` (BaseIngestor only reads `.name`
    # via `get_source_url` fallback, which we override anyway).
    class _MinimalManifest:
        name = manifest.get("name", "futureproof-data")

    ingestor = GemmaAiExposureIngestor(source, _MinimalManifest())
    fetch_method = next(iter(source.fetch.keys())) if source.fetch else "fixture_file"
    return ingestor.ingest(method=fetch_method)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(message)s",
    )
    result = _run_cli()
    print(f"Bronze ingest complete: {result}")
