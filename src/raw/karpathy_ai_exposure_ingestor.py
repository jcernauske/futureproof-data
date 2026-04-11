"""Ingestor for Karpathy AI Exposure Scores.

Ingests AI exposure scores (0-10) for 342 BLS occupations from Andrej
Karpathy's karpathy/jobs GitHub repository.  Two files are fetched and
joined: scores.json (keyed by slug) and occupations.csv (maps slug to
SOC code and BLS metadata).

Grain: occupation slug (kebab-case identifier).
"""

import csv
import io
import json
import logging
from pathlib import Path
from typing import Any

import requests
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

from brightsmith.bronze.base_ingestor import BaseIngestor

logger = logging.getLogger(__name__)


class KarpathyAiExposureIngestor(BaseIngestor):
    """Ingests Karpathy AI exposure scores into the bronze zone.

    Data source: Two files from the karpathy/jobs GitHub repository:
      - scores.json: {"slug": {"exposure": N, "rationale": "..."}, ...}
      - occupations.csv: slug, soc_code, title, category, and BLS metadata

    Grain: occupation (slug)

    Key considerations:
    - Some occupations in occupations.csv have empty SOC codes -- preserve as null
    - exposure_score is 0-10 integer
    - Carry forward median_pay_annual, num_jobs_2024, entry_education for cross-validation
    - Falls back to local cache if GitHub returns HTTP error
    """

    SCORES_URL = "https://raw.githubusercontent.com/karpathy/jobs/master/scores.json"
    OCCUPATIONS_URL = "https://raw.githubusercontent.com/karpathy/jobs/master/occupations.csv"
    FALLBACK_DIR = "data/raw/karpathy_cache"
    USER_AGENT = "FutureProof/0.1 (jeff@hyenastudios.com)"

    def fetch(self, entities: dict, method: str, **kwargs) -> dict:
        """Fetch scores.json and occupations.csv, join on slug.

        Args:
            entities: {entity_id: label} dict from source config.
            method: Fetch method name.
            **kwargs: Supports ``cache_dir`` for local fallback path,
                      ``scores_path`` and ``occupations_path`` for direct
                      local file paths (used in tests).

        Returns:
            Dict mapping each entity_id to a dict with keys
            ``scores``, ``occupations``, and ``source_method``.
        """
        scores_path = kwargs.get("scores_path")
        occupations_path = kwargs.get("occupations_path")

        if scores_path and occupations_path:
            # Direct local file paths (test mode)
            scores = self._read_scores_file(Path(scores_path))
            occupations = self._read_occupations_file(Path(occupations_path))
            source_method = "local_cache"
        else:
            scores, occupations, source_method = self._download_or_fallback(
                kwargs.get("cache_dir")
            )

        payload = {
            "scores": scores,
            "occupations": occupations,
            "source_method": source_method,
        }
        return {entity_id: payload for entity_id in entities}

    def _download_or_fallback(self, cache_dir: str | None = None) -> tuple:
        """Try HTTP download, fall back to local cache on failure.

        Returns:
            (scores_by_slug_dict, occupations_list, source_method) tuple.
        """
        headers = {"User-Agent": self.USER_AGENT}
        fallback = Path(cache_dir) if cache_dir else Path(self.FALLBACK_DIR)

        try:
            scores_resp = requests.get(self.SCORES_URL, headers=headers, timeout=30)
            scores_resp.raise_for_status()
            scores = self._normalize_scores(json.loads(scores_resp.text))

            occ_resp = requests.get(self.OCCUPATIONS_URL, headers=headers, timeout=30)
            occ_resp.raise_for_status()
            occupations = self._parse_occupations_csv(occ_resp.text)

            source_method = "github_download"
            logger.info(
                "Downloaded %d scores and %d occupations from GitHub",
                len(scores),
                len(occupations),
            )
            return scores, occupations, source_method

        except Exception:
            logger.warning(
                "GitHub download failed, falling back to %s", fallback
            )
            scores = self._read_scores_file(fallback / "scores.json")
            occupations = self._read_occupations_file(fallback / "occupations.csv")
            return scores, occupations, "local_cache"

    @staticmethod
    def _normalize_scores(raw: dict | list) -> dict:
        """Normalize scores.json into a dict keyed by slug.

        The actual file is a JSON array of objects:
            [{"slug": "...", "exposure": N, "rationale": "..."}, ...]
        The spec originally described it as a dict keyed by slug.
        This method handles both formats for robustness.
        """
        if isinstance(raw, dict):
            return raw
        # Array of objects -- convert to dict keyed by slug
        return {entry["slug"]: entry for entry in raw}

    @staticmethod
    def _read_scores_file(path: Path) -> dict:
        """Read scores.json from a local file and normalize to dict by slug."""
        with open(path) as f:
            raw = json.load(f)
        if isinstance(raw, list):
            return {entry["slug"]: entry for entry in raw}
        return raw

    @staticmethod
    def _read_occupations_file(path: Path) -> list[dict]:
        """Read occupations.csv from a local file."""
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    @staticmethod
    def _parse_occupations_csv(text: str) -> list[dict]:
        """Parse occupations.csv from a string."""
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)

    def flatten(self, raw_data: Any, entity_id: str) -> list[dict]:
        """Join scores and occupations on slug, produce flat rows.

        Args:
            raw_data: Dict with keys ``scores``, ``occupations``,
                      ``source_method`` from fetch().
            entity_id: Logical entity identifier.

        Returns:
            List of flat dicts with lowercase keys matching the Iceberg
            schema.  Does NOT add metadata fields -- the framework
            handles those.
        """
        scores = raw_data["scores"]
        occupations = raw_data["occupations"]

        # Build a lookup from slug -> occupation row
        occ_by_slug: dict[str, dict] = {}
        for occ in occupations:
            slug = occ.get("slug", "").strip()
            if slug:
                occ_by_slug[slug] = occ

        flat_rows: list[dict] = []
        unmatched_slugs: list[str] = []

        for slug, score_data in scores.items():
            occ = occ_by_slug.get(slug)
            if occ is None:
                unmatched_slugs.append(slug)
                continue

            record = {
                "slug": slug,
                "occupation_title": self._coerce_string(occ.get("title")),
                "category": self._coerce_string(occ.get("category")),
                "soc_code": self._coerce_soc(occ.get("soc_code")),
                "exposure_score": self._coerce_int(score_data.get("exposure")),
                "rationale": self._coerce_string(score_data.get("rationale")),
                "median_pay_annual": self._coerce_double(occ.get("median_pay_annual")),
                "num_jobs_2024": self._coerce_long(occ.get("num_jobs_2024")),
                "entry_education": self._coerce_string(occ.get("entry_education")),
            }
            flat_rows.append(record)

        if unmatched_slugs:
            logger.warning(
                "%d slugs in scores.json not found in occupations.csv: %s",
                len(unmatched_slugs),
                unmatched_slugs[:5],
            )

        logger.info("Flattened %d occupation rows", len(flat_rows))
        return flat_rows

    def get_source_url(self, entity_id: Any, method: str) -> str:
        """Return the source URL for lineage/audit purposes."""
        return self.SCORES_URL

    @staticmethod
    def _coerce_string(value: Any) -> str | None:
        """Coerce to string or None."""
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    @staticmethod
    def _coerce_soc(value: Any) -> str | None:
        """Coerce SOC code to string or None if empty."""
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        """Coerce to int or None."""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _coerce_double(value: Any) -> float | None:
        """Coerce to float or None. Handles comma-formatted numbers."""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip().replace(",", "").replace("$", "")
            if not value:
                return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _coerce_long(value: Any) -> int | None:
        """Coerce to long int or None. Handles comma-formatted numbers."""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip().replace(",", "")
            if not value:
                return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def get_schema(self) -> Schema:
        """Define the Iceberg table schema for bronze.karpathy_ai_exposure.

        Matches the fields returned by flatten() plus framework metadata.
        Grain is slug.
        """
        return Schema(
            # Grain field
            NestedField(1, "slug", StringType(), required=True),
            # Data fields
            NestedField(2, "occupation_title", StringType(), required=True),
            NestedField(3, "category", StringType(), required=True),
            NestedField(4, "soc_code", StringType(), required=False),
            NestedField(5, "exposure_score", IntegerType(), required=True),
            NestedField(6, "rationale", StringType(), required=True),
            NestedField(7, "median_pay_annual", DoubleType(), required=False),
            NestedField(8, "num_jobs_2024", LongType(), required=False),
            NestedField(9, "entry_education", StringType(), required=False),
            # Metadata
            NestedField(10, "ingested_at", TimestampType(), required=True),
            NestedField(11, "source_url", StringType(), required=True),
            NestedField(12, "source_method", StringType(), required=True),
            NestedField(13, "load_date", DateType(), required=True),
        )
