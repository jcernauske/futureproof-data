"""Ingestor for the Anthropic Economic Index dataset.

Ingests observed AI exposure data from the Anthropic/EconomicIndex
HuggingFace dataset.  The dataset is the missing "observed exposure"
signal needed for the S4 three-signal composite: Anthropic measures
what AI *is* doing (empirical adoption) in millions of real Claude
conversations, mapped to O*NET tasks.

Grain: one row per (O*NET task, SOC code) pair. Task-to-SOC is
many-to-many (up to 34-way fan-out in the 2025-03-27 release); one
unmatched placeholder row (``task_name='none'``) carries ``soc_code``
= NULL and is kept in Bronze but excluded from Silver per-SOC
aggregation.

The data lives as plain CSVs under ``data/raw/anthropic_economic_index/``
(cloned via ``git lfs``). Three files are read per release and LEFT
JOINed on the task text:

  1. ``task_pct_v2.csv``              — task_name, pct
  2. ``automation_vs_augmentation_by_task.csv``
                                      — task_name, feedback_loop,
                                        directive, task_iteration,
                                        validation, learning, filtered
  3. ``onet_task_statements.csv``     — O*NET-SOC Code, Title, Task ID,
                                        Task, Task Type, ...
                                        (used as the SOC bridge since
                                        no ``onet_task_mappings.csv``
                                        exists in the 2025-03-27 release)

Key implementation notes
------------------------
- ``task_pct_v2.pct`` is already in 0-100 percent units — the column
  sums to 100.0 across the full task table (global share). We do
  NOT multiply by 100. Per-Bronze-row ``task_pct`` is
  ``pct / n_soc_per_task`` so summing across the Bronze fan-out
  preserves the ~100% global invariant.
- The v2 automation file splits into 5 modes plus ``filtered``;
  following Anthropic's own v2 methodology:
    automation   = directive + feedback_loop
    augmentation = task_iteration + validation + learning
    (``learning`` = user-learns-from-Claude, Claude is assisting)
- Task text joins are case-insensitive and trim trailing punctuation
  (O*NET tasks end with "." but task_pct_v2 is inconsistent).
- CSVs are read in chunks of 50,000 rows for memory safety.
- The ``PrivacySuppressed`` sentinel does not appear in this source
  but we keep the coercion helper for defensive parity with other
  FutureProof ingestors.
"""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path
from typing import Any

from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.bronze.base_ingestor import BaseIngestor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOURCE_URL = "https://huggingface.co/datasets/Anthropic/EconomicIndex"
USER_AGENT = "FutureProof/0.1 (jeff@hyenastudios.com)"

# Release preference order (spec §Zone 0 Release Selection).
RELEASE_PREFERENCE: tuple[str, ...] = (
    "release_2026_03_24",
    "release_2026_01_15",
    "release_2025_03_27",
)

# File names inside a release directory.  Paths differ per release
# (some releases nest under ``data/``); the ingestor resolves them
# lazily via ``_find_release_files``.
TASK_PCT_FILENAME = "task_pct_v2.csv"
AUTOMATION_FILENAME = "automation_vs_augmentation_by_task.csv"
TASK_STATEMENTS_FILENAME = "onet_task_statements.csv"

DATASET_ROOT = "data/raw/anthropic_economic_index"
CACHE_ROOT = "data/raw/anthropic_economic_index_cache"

# CSV chunk size (spec rule: read CSVs in chunks of 50,000 rows).
CSV_CHUNK_SIZE = 50_000

# Sentinel string -> None. Not observed in this source, kept for parity.
SENTINEL_VALUES: frozenset[str] = frozenset({
    "PrivacySuppressed", "PS", "NA", "NULL", "",
})

# Canonical SOC format: two digits, dash, four digits (e.g. "15-1252").
SOC_CODE_PATTERN = re.compile(r"^\d{2}-\d{4}$")

# Required column sets per source CSV — checked at ingestion start so a
# malformed / schema-drifted source file fails loudly instead of silently
# emitting None-filled rows (chaos-monkey P2 Gap 2).
REQUIRED_COLUMNS: dict[str, frozenset[str]] = {
    TASK_PCT_FILENAME: frozenset({"task_name", "pct"}),
    AUTOMATION_FILENAME: frozenset({
        "task_name",
        "feedback_loop",
        "directive",
        "task_iteration",
        "validation",
        "learning",
        "filtered",
    }),
    # onet_task_statements uses the O*NET canonical header names.
    # Fixture aliases (task_statement / task_name / soc_code) are
    # accepted elsewhere in the code — header-check only enforces the
    # canonical O*NET column names when the file is named
    # onet_task_statements.csv. Fixture files use a shorter alias name
    # and are exempt from the required-column check.
    TASK_STATEMENTS_FILENAME: frozenset({
        "O*NET-SOC Code",
        "Task ID",
        "Task",
    }),
}


class AnthropicEconomicIndexIngestor(BaseIngestor):
    """Ingest the Anthropic Economic Index into the Bronze zone.

    Produces one row per O*NET task (~3,500 rows at the 2025-03-27
    release) with task text, pct usage, 5-axis automation breakdown,
    SOC code, and occupation title. Silver aggregates to SOC grain.
    """

    def fetch(self, entities: dict, method: str, **kwargs: Any) -> dict:
        """Locate the release directory and read the three source CSVs.

        Args:
            entities: ``{entity_id: label}`` from source config.
            method: Fetch method (``hf_git_clone`` is canonical; the
                actual files are read from the already-cloned local
                mirror).
            **kwargs: Supports ``dataset_root`` for test-mode override.
                Tests pass a fixtures directory containing the three
                CSVs directly (no release subdirectory).

        Returns:
            ``{entity_id: payload}`` with the same payload repeated for
            every entity_id. Payload has keys:
                - task_pct_rows: list of dicts
                - automation_rows: list of dicts
                - task_statements_rows: list of dicts
                - source_release: release directory name (or "fixtures")
                - source_method: "hf_git_clone" or "local_cache"
        """
        dataset_root = kwargs.get("dataset_root")
        if dataset_root is not None:
            # Test mode: caller points us at a flat fixtures dir
            base = Path(dataset_root)
            release_name = kwargs.get("release_name") or "fixtures"
            files = self._resolve_fixture_files(base)
            source_method = "fixtures"
        else:
            base, release_name, source_method = self._select_release_dir()
            files = self._find_release_files(base)

        # Fast-fail header check before reading full files. A source
        # file with missing required columns is a schema drift or a
        # chaos-monkey scenario — raise with a clear message listing
        # exactly which columns are missing so downstream does not
        # silently emit None-filled rows.
        self._validate_csv_headers(
            files["task_pct"], REQUIRED_COLUMNS[TASK_PCT_FILENAME]
        )
        self._validate_csv_headers(
            files["automation"], REQUIRED_COLUMNS[AUTOMATION_FILENAME]
        )
        # task_statements: accept either the canonical O*NET header set
        # or the fixture-alias header set used in tests. If NEITHER
        # matches we raise — fast-fail rather than silently fall through
        # to all-None SOC rows.
        self._validate_task_statements_headers(files["task_statements"])

        task_pct_rows = self._read_csv_chunked(files["task_pct"])
        automation_rows = self._read_csv_chunked(files["automation"])
        task_statements_rows = self._read_csv_chunked(files["task_statements"])

        logger.info(
            "Loaded Anthropic Economic Index release=%s "
            "task_pct=%d automation=%d task_statements=%d",
            release_name,
            len(task_pct_rows),
            len(automation_rows),
            len(task_statements_rows),
        )

        payload = {
            "task_pct_rows": task_pct_rows,
            "automation_rows": automation_rows,
            "task_statements_rows": task_statements_rows,
            "source_release": release_name,
            "source_method": source_method,
        }
        return {entity_id: payload for entity_id in entities}

    # ------------------------------------------------------------------
    # Release resolution
    # ------------------------------------------------------------------

    def _select_release_dir(self) -> tuple[Path, str, str]:
        """Pick the first release (per preference order) that has task_pct_v2.

        Returns:
            (release_directory, release_name, source_method).

        Raises:
            FileNotFoundError: No release (under either the live clone
                or the cache) contains ``task_pct_v2.csv``.
        """
        roots = [
            (Path(DATASET_ROOT), "hf_git_clone"),
            (Path(CACHE_ROOT), "local_cache"),
        ]
        for root, method in roots:
            if not root.exists():
                continue
            for release_name in RELEASE_PREFERENCE:
                candidate = root / release_name
                if not candidate.is_dir():
                    continue
                # Search recursively — some releases nest files under data/
                if self._has_task_pct_v2(candidate):
                    logger.info(
                        "Using Anthropic Economic Index release %s from %s",
                        release_name, method,
                    )
                    return candidate, release_name, method

        raise FileNotFoundError(
            "No Anthropic Economic Index release containing "
            f"{TASK_PCT_FILENAME} was found under {DATASET_ROOT} or "
            f"{CACHE_ROOT}. Clone the dataset with "
            "`git clone https://huggingface.co/datasets/Anthropic/"
            "EconomicIndex data/raw/anthropic_economic_index && "
            "cd data/raw/anthropic_economic_index && git lfs pull`."
        )

    @staticmethod
    def _has_task_pct_v2(release_dir: Path) -> bool:
        """Return True if ``task_pct_v2.csv`` exists anywhere under the release."""
        return any(release_dir.rglob(TASK_PCT_FILENAME))

    @staticmethod
    def _find_release_files(release_dir: Path) -> dict[str, Path]:
        """Locate the three source CSVs under a release directory.

        Falls back to searching the sibling ``release_2025_03_27`` for
        ``onet_task_statements.csv`` if the selected release omits it
        (newer releases do not always re-publish the O*NET bridge).
        """
        def first(name: str, search_roots: list[Path]) -> Path:
            for root in search_roots:
                matches = list(root.rglob(name))
                if matches:
                    return matches[0]
            raise FileNotFoundError(
                f"Could not locate {name} under {release_dir} "
                f"(or sibling 2025-03-27 release as fallback)."
            )

        # Primary search: inside the release
        search_roots: list[Path] = [release_dir]
        # Fallback for onet_task_statements.csv: older releases always have it
        parent = release_dir.parent
        sibling = parent / "release_2025_03_27"
        if sibling.exists() and sibling != release_dir:
            search_roots.append(sibling)

        return {
            "task_pct": first(TASK_PCT_FILENAME, [release_dir]),
            "automation": first(AUTOMATION_FILENAME, [release_dir]),
            "task_statements": first(TASK_STATEMENTS_FILENAME, search_roots),
        }

    @staticmethod
    def _resolve_fixture_files(fixtures_dir: Path) -> dict[str, Path]:
        """Locate CSVs in a flat fixtures directory (test mode).

        Accepts both the canonical names (``task_pct_v2.csv``, etc.)
        and the shorter fixture aliases used in
        ``tests/fixtures/anthropic_economic_index/``:

          - task_pct_sample.csv
          - automation_sample.csv
          - task_mappings_sample.csv (acts as the task_statements bridge)
        """
        aliases: dict[str, list[str]] = {
            "task_pct": [TASK_PCT_FILENAME, "task_pct_sample.csv"],
            "automation": [AUTOMATION_FILENAME, "automation_sample.csv"],
            "task_statements": [
                TASK_STATEMENTS_FILENAME,
                "task_mappings_sample.csv",
            ],
        }

        resolved: dict[str, Path] = {}
        for key, candidates in aliases.items():
            for name in candidates:
                candidate = fixtures_dir / name
                if candidate.exists():
                    resolved[key] = candidate
                    break
            else:
                raise FileNotFoundError(
                    f"Fixtures directory {fixtures_dir} is missing a file "
                    f"matching any of {candidates}"
                )
        return resolved

    # ------------------------------------------------------------------
    # CSV reading
    # ------------------------------------------------------------------

    @staticmethod
    def _peek_csv_headers(path: Path) -> list[str]:
        """Return the header row of a CSV without reading any data rows.

        Raises FileNotFoundError if the file does not exist and
        ValueError if the file is empty (no header line at all).
        """
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
            except StopIteration as exc:
                raise ValueError(
                    f"CSV {path} is empty (no header row)"
                ) from exc
        return [h.strip() for h in headers]

    @classmethod
    def _validate_csv_headers(
        cls,
        path: Path,
        required: frozenset[str],
    ) -> None:
        """Raise ValueError if any required column is missing from the CSV header.

        Fast-fail guard invoked at ingestion start (before reading the
        full file body). Addresses chaos-monkey P2 Gap 2: a source file
        with drifted headers used to fall through to ``csv.DictReader``,
        emit None for every missing field, and produce a Bronze table
        full of silent data loss. Now we raise with an explicit list of
        missing columns so the failure is loud and diagnosable.
        """
        headers = set(cls._peek_csv_headers(path))
        missing = required - headers
        if missing:
            raise ValueError(
                f"CSV {path.name} is missing required columns: "
                f"{sorted(missing)}. Found columns: {sorted(headers)}. "
                "This indicates source schema drift — inspect the file "
                "and update the ingestor if the source format has changed."
            )

    @classmethod
    def _validate_task_statements_headers(cls, path: Path) -> None:
        """Validate onet_task_statements.csv (canonical or fixture-alias headers).

        The production file uses canonical O*NET headers
        ("O*NET-SOC Code", "Task ID", "Task"). Test fixtures use the
        same canonical headers, but earlier fixture formats used
        snake_case aliases ("soc_code", "task_id", "task_statement" /
        "task_name"). Accept either shape so fixtures stay flexible
        while still fast-failing on genuinely malformed files.
        """
        headers = set(cls._peek_csv_headers(path))

        canonical = REQUIRED_COLUMNS[TASK_STATEMENTS_FILENAME]
        if canonical.issubset(headers):
            return

        # Alias form — must provide SOC code, task id, and task text.
        soc_aliases = {"O*NET-SOC Code", "onet_soc_code", "soc_code"}
        task_id_aliases = {"Task ID", "task_id"}
        task_text_aliases = {"Task", "task_statement", "task_name"}

        if (
            headers & soc_aliases
            and headers & task_id_aliases
            and headers & task_text_aliases
        ):
            return

        raise ValueError(
            f"CSV {path.name} is missing required task-statement columns. "
            f"Needed one of SOC {sorted(soc_aliases)}, one of task-id "
            f"{sorted(task_id_aliases)}, and one of task-text "
            f"{sorted(task_text_aliases)}. Found columns: "
            f"{sorted(headers)}."
        )

    @staticmethod
    def _read_csv_chunked(path: Path) -> list[dict[str, str]]:
        """Read a CSV as dict rows in chunks of CSV_CHUNK_SIZE rows.

        The stdlib csv.DictReader is already streaming, but we
        materialize in explicit chunks and log progress so large files
        do not look hung.  The total row list is still held in memory
        (~20K rows max for this source, ~few MB).
        """
        rows: list[dict[str, str]] = []
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            chunk: list[dict[str, str]] = []
            for i, row in enumerate(reader, start=1):
                chunk.append(row)
                if i % CSV_CHUNK_SIZE == 0:
                    rows.extend(chunk)
                    chunk.clear()
                    logger.debug("Read %d rows from %s...", i, path.name)
            if chunk:
                rows.extend(chunk)
        logger.info("Read %d rows from %s", len(rows), path.name)
        return rows

    # ------------------------------------------------------------------
    # Flatten
    # ------------------------------------------------------------------

    def flatten(self, raw_data: Any, entity_id: Any) -> list[dict]:
        """Join three CSVs on task text and emit one row per (task, soc) pair.

        The LEFT base is ``task_pct_v2``: every task with observed usage
        gets at least one Bronze row. SOC codes are looked up from
        ``onet_task_statements`` by task text (case-insensitive, trailing
        punctuation normalized); task-to-SOC is many-to-many, so a task
        that maps to N distinct SOCs emits N Bronze rows. The 5-axis
        automation breakdown is joined from
        ``automation_vs_augmentation_by_task``.

        Per-row ``task_pct`` is ``raw_pct / n_soc_per_task`` — this
        conserves the global 100% invariant across the fan-out so
        ``SUM(task_pct)`` across all Bronze rows stays ~100 regardless
        of how many SOCs each task maps to.

        Tasks with no O*NET SOC match (e.g. the ``task_name='none'``
        placeholder) emit exactly one Bronze row with ``soc_code=NULL``
        and ``task_pct`` = raw_pct (no split).

        Bronze grain is ``[task_id, soc_code]`` — the composite of
        O*NET task ID and SOC code. ``task_id`` alone is NOT unique.
        """
        task_pct_rows: list[dict[str, str]] = raw_data["task_pct_rows"]
        automation_rows: list[dict[str, str]] = raw_data["automation_rows"]
        task_statements_rows: list[dict[str, str]] = raw_data[
            "task_statements_rows"
        ]
        source_release: str = raw_data["source_release"]

        automation_by_key = self._index_automation(automation_rows)
        statements_by_key, malformed_only_keys = self._index_task_statements(
            task_statements_rows
        )

        flat_rows: list[dict] = []
        seen_grain: set[tuple[str, str | None]] = set()

        for row in task_pct_rows:
            task_name_raw = row.get("task_name") or row.get("Task") or ""
            task_name_key = self._normalize_task_text(task_name_raw)
            if not task_name_key:
                continue

            stmts = statements_by_key.get(task_name_key) or []
            auto = automation_by_key.get(task_name_key)

            # task_pct_v2.pct is already 0-100 percent units (global
            # share; source-level sum = 100.0). Keep as-is.
            raw_pct = self._coerce_double(row.get("pct"))

            automation_pct, augmentation_pct = self._collapse_automation(auto)

            if not stmts:
                # No O*NET SOC match after filtering. THREE cases:
                #   (a) Task not in the O*NET bridge at all (e.g. the
                #       ``task_name='none'`` placeholder). Expected ->
                #       emit a single NULL-SOC Bronze row. Silver
                #       filters these out during per-SOC aggregation.
                #   (b) Task text appears in the O*NET bridge but every
                #       SOC value is malformed (chaos-monkey P1:
                #       dash-less, wrong digit count, garbled, etc.) ->
                #       DROP the task entirely. Emitting a NULL-SOC row
                #       here would both inflate the NULL-SOC count past
                #       the single row expected by DQ rule RAW-AEI-017
                #       AND silently hide upstream data loss. Dropping
                #       surfaces the issue: Silver row count dips and
                #       chaos-monkey sees it.
                #   (c) Same situation as (b) but arrived at from a
                #       task that simply isn't in the bridge. Treated
                #       as (a).
                if task_name_key in malformed_only_keys:
                    logger.warning(
                        "Dropping Anthropic task %r: O*NET bridge "
                        "entries present but all SOC values were "
                        "malformed (chaos-monkey P1 guard)",
                        task_name_raw,
                    )
                    continue
                task_id = task_name_key
                grain = (task_id, None)
                if grain in seen_grain:
                    continue
                seen_grain.add(grain)
                flat_rows.append({
                    "task_id": task_id,
                    "task_statement": self._coerce_string(task_name_raw),
                    "soc_code": None,
                    "soc_title": None,
                    "task_pct": raw_pct,
                    "automation_pct": automation_pct,
                    "augmentation_pct": augmentation_pct,
                    "source_release": source_release,
                })
                continue

            # Many-to-many: one Bronze row per (task, soc) pair.
            # Split raw_pct by n_soc so the global sum is conserved.
            n_soc = len(stmts)
            split_pct = (
                raw_pct / n_soc if raw_pct is not None and n_soc > 0 else None
            )

            for stmt in stmts:
                task_id = stmt.get("task_id") or task_name_key
                soc_code = stmt.get("soc_code")
                grain = (task_id, soc_code)
                if grain in seen_grain:
                    continue
                seen_grain.add(grain)

                flat_rows.append({
                    "task_id": task_id,
                    "task_statement": self._coerce_string(task_name_raw),
                    "soc_code": soc_code,
                    "soc_title": stmt.get("soc_title"),
                    "task_pct": split_pct,
                    "automation_pct": automation_pct,
                    "augmentation_pct": augmentation_pct,
                    "source_release": source_release,
                })

        logger.info(
            "Flattened %d Anthropic Economic Index (task, soc) rows "
            "(SOC-matched: %d)",
            len(flat_rows),
            sum(1 for r in flat_rows if r["soc_code"]),
        )
        return flat_rows

    # ------------------------------------------------------------------
    # Join helpers
    # ------------------------------------------------------------------

    @classmethod
    def _index_automation(
        cls,
        automation_rows: list[dict[str, str]],
    ) -> dict[str, dict[str, float | None]]:
        """Index the 5-axis automation file by normalized task text.

        Returns a dict mapping normalized task text to a sub-dict with
        float values (or None) for the 5 axes + ``filtered``.
        """
        indexed: dict[str, dict[str, float | None]] = {}
        for row in automation_rows:
            key = cls._normalize_task_text(row.get("task_name") or "")
            if not key:
                continue
            indexed[key] = {
                "feedback_loop": cls._coerce_double(row.get("feedback_loop")),
                "directive": cls._coerce_double(row.get("directive")),
                "task_iteration": cls._coerce_double(row.get("task_iteration")),
                "validation": cls._coerce_double(row.get("validation")),
                "learning": cls._coerce_double(row.get("learning")),
                "filtered": cls._coerce_double(row.get("filtered")),
            }
        return indexed

    @classmethod
    def _index_task_statements(
        cls,
        task_statements_rows: list[dict[str, str]],
    ) -> tuple[dict[str, list[dict[str, str | None]]], set[str]]:
        """Index O*NET task statements by normalized task text.

        Task-to-SOC is many-to-many in O*NET: the same task statement
        can appear under multiple O*NET-SOC codes via generalized work
        activities.

        Returns a 2-tuple:
          1. ``indexed``: normalized_task_key -> list of distinct
             ``{task_id, soc_code, soc_title}`` dicts, with blank /
             malformed SOCs filtered out and (task_key, soc_code) pairs
             deduped.
          2. ``malformed_only_keys``: set of normalized task keys that
             appeared in the source with at least one row BUT whose
             every SOC value was malformed (rejected by
             ``_normalize_onet_soc``). The caller uses this to
             distinguish "task isn't in the O*NET bridge at all"
             (emit a NULL-SOC row, e.g. the ``task_name='none'``
             placeholder and genuinely-unmapped tasks) from "task is in
             the O*NET bridge but every SOC was garbage"
             (drop the task entirely to avoid inflating the NULL-SOC
             row count past the one expected row -- see DQ rule
             RAW-AEI-017).
        """
        indexed: dict[str, list[dict[str, str | None]]] = {}
        seen_pairs: dict[str, set[str]] = {}
        # Keys that appeared in the source at all (even with bad SOCs)
        seen_keys: set[str] = set()
        for row in task_statements_rows:
            task_text = (
                row.get("Task")
                or row.get("task_statement")
                or row.get("task_name")
                or ""
            )
            key = cls._normalize_task_text(task_text)
            if not key:
                continue
            seen_keys.add(key)

            onet_soc = (
                row.get("O*NET-SOC Code")
                or row.get("onet_soc_code")
                or row.get("soc_code")
                or ""
            )
            soc_code = cls._normalize_onet_soc(onet_soc)
            if soc_code is None:
                continue

            pair_set = seen_pairs.setdefault(key, set())
            if soc_code in pair_set:
                continue
            pair_set.add(soc_code)

            indexed.setdefault(key, []).append({
                "task_id": cls._coerce_string(
                    row.get("Task ID") or row.get("task_id")
                ),
                "soc_code": soc_code,
                "soc_title": cls._coerce_string(
                    row.get("Title") or row.get("soc_title")
                ),
            })
        malformed_only_keys = seen_keys - set(indexed.keys())
        return indexed, malformed_only_keys

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_task_text(value: str | None) -> str:
        """Normalize task text for cross-file joining.

        Lowercases, collapses whitespace, strips trailing period so that
        "Direct X." and "direct x" compare equal. O*NET canonical
        statements end in "." but task_pct_v2 is inconsistent.
        """
        if value is None:
            return ""
        s = str(value).strip().lower()
        if not s:
            return ""
        # Collapse interior whitespace
        s = " ".join(s.split())
        # Strip trailing period (O*NET convention)
        if s.endswith("."):
            s = s[:-1]
        return s

    @staticmethod
    def _normalize_onet_soc(value: str | None) -> str | None:
        """Normalize and validate an O*NET-SOC code to canonical SOC form ``XX-XXXX``.

        Pipeline:
          1. Reject ``None``, empty, whitespace-only, or sentinel strings
             (``"nan"`` / ``"none"`` / ``"null"``) -> None.
          2. Strip the O*NET overlay suffix (``.00`` / ``.01`` / ``.NN``).
             Anthropic publishes ``XX-XXXX.NN``; BLS/SOC downstream uses
             the 7-char detail code.
          3. If the result already matches the canonical ``^\\d{2}-\\d{4}$``
             regex, return it.
          4. If the result is 6 digits with no dash (e.g. ``"151252"``),
             unambiguously insert the dash after position 2
             (``"15-1252"``) and accept. This covers the chaos-monkey P1
             scenario where a malformed upstream row drops the dash.
          5. Anything else — too few digits, too many digits, embedded
             whitespace, letters, wrong dash position — is rejected and
             returns None.

        Malformed SOC design choice (chaos-monkey P1 fix)
        -------------------------------------------------
        When this function returns None for a task-statement row, the
        caller ``_index_task_statements`` drops that (task, SOC) mapping.
        If ALL of a task's SOC mappings are malformed the task will have
        zero valid SOC matches and ``flatten`` will treat it the same as
        the genuine ``task_name='none'`` placeholder — with one
        critical difference: we must NOT emit an extra NULL-SOC Bronze
        row for real tasks, because DQ rule RAW-AEI-017 expects exactly
        one NULL-SOC row (the real ``task_name='none'`` placeholder).
        The safer choice is therefore to DROP the task entirely when it
        has no valid SOC match AND is not the literal ``"none"``
        placeholder. This is enforced in ``flatten`` (not here); this
        function is the source of truth for "is the SOC itself valid?".

        Returns:
            Canonical ``XX-XXXX`` SOC code string, or None if the input
            is empty, malformed, or ambiguous.
        """
        if value is None:
            return None
        s = str(value).strip()
        if not s or s.lower() in {"nan", "none", "null"}:
            return None

        # Drop O*NET overlay suffix after the dot (``.00`` / ``.01`` / etc.)
        if "." in s:
            s = s.split(".", 1)[0]

        # Already canonical: two digits, dash, four digits.
        if SOC_CODE_PATTERN.match(s):
            return s

        # Dash-less 6-digit heuristic recovery. Only 6 digits is
        # unambiguous (XX + XXXX). 5 digits (XX + XXX) or 7 digits
        # (XX + XXXXX) would be ambiguous — where does the dash go? —
        # so we reject them.
        if len(s) == 6 and s.isdigit():
            return f"{s[:2]}-{s[2:]}"

        # Any other shape is malformed. Examples caught here:
        #   - "151252"    -> recovered by the 6-digit branch above
        #   - "15125"     -> rejected (5 digits, ambiguous)
        #   - "1512522"   -> rejected (7 digits, ambiguous)
        #   - "15-125"    -> rejected (dash present but wrong shape)
        #   - "15-12522"  -> rejected (dash present but wrong shape)
        #   - "ABC-1252"  -> rejected (non-numeric)
        #   - "15 1252"   -> rejected (no dash, has space)
        return None

    @staticmethod
    def _collapse_automation(
        axes: dict[str, float | None] | None,
    ) -> tuple[float | None, float | None]:
        """Collapse Anthropic's 5-axis breakdown into automation/augmentation %.

        Anthropic classifies each conversation as one of five
        interaction types (plus a ``filtered`` bucket for data excluded
        from analysis). Following Anthropic's own v2 methodology
        (Economic Index release notes, 2025):

          automation   = directive + feedback_loop
          augmentation = task_iteration + validation + learning

        ``learning`` here is *user-learns-from-Claude*: Claude is
        assisting the human, so it belongs with augmentation, not
        automation. (This corrects an earlier miscategorization where
        ``learning`` was placed on the automation side.)

        Both returned as percents (0-100). Returns (None, None) when
        the task has no automation data OR when ``filtered`` covers the
        entire task (no usable signal).

        By construction the 6 fields sum to exactly 1.0 per row, so
        ``automation_pct + augmentation_pct + filtered*100 == 100`` for
        every non-fully-filtered task.
        """
        if axes is None:
            return None, None

        filtered = axes.get("filtered")
        if filtered is not None and filtered >= 0.999:
            # Entire task was filtered out — no usable classification
            return None, None

        directive = axes.get("directive") or 0.0
        feedback_loop = axes.get("feedback_loop") or 0.0
        task_iteration = axes.get("task_iteration") or 0.0
        validation = axes.get("validation") or 0.0
        learning = axes.get("learning") or 0.0

        automation = (directive + feedback_loop) * 100.0
        augmentation = (task_iteration + validation + learning) * 100.0

        # If all axes are zero and filtered is zero, still count as 0/0
        return automation, augmentation

    # ------------------------------------------------------------------
    # Coercion (defensive parity with peer ingestors)
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_string(value: Any) -> str | None:
        """Coerce to string or None. Also nulls SENTINEL_VALUES."""
        if value is None:
            return None
        s = str(value).strip()
        if not s or s in SENTINEL_VALUES:
            return None
        return s

    @staticmethod
    def _coerce_double(value: Any) -> float | None:
        """Coerce to float or None. Handles sentinel strings."""
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        if not s or s in SENTINEL_VALUES:
            return None
        try:
            return float(s)
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Framework hooks
    # ------------------------------------------------------------------

    def get_source_url(self, entity_id: Any, method: str) -> str:
        """Return the HuggingFace dataset URL for lineage."""
        return SOURCE_URL

    def get_schema(self) -> Schema:
        """Iceberg schema for raw.anthropic_economic_index.

        Grain: composite ``[task_id, soc_code]`` — the (task, SOC) pair.
        ``soc_code`` is nullable to accommodate tasks with no O*NET
        match (e.g. the ``task_name='none'`` placeholder row).

        Matches the Raw Schema declared in
        ``docs/specs/raw-ingest-anthropic-economic-index.md §"Raw Schema"``.
        """
        return Schema(
            # Grain (composite: task_id + soc_code)
            NestedField(1, "task_id", StringType(), required=True),
            # Core data
            NestedField(2, "task_statement", StringType(), required=True),
            NestedField(3, "soc_code", StringType(), required=False),
            NestedField(4, "soc_title", StringType(), required=False),
            NestedField(5, "task_pct", DoubleType(), required=False),
            NestedField(6, "automation_pct", DoubleType(), required=False),
            NestedField(7, "augmentation_pct", DoubleType(), required=False),
            NestedField(8, "source_release", StringType(), required=True),
            # Framework metadata
            NestedField(9, "ingested_at", TimestampType(), required=True),
            NestedField(10, "source_url", StringType(), required=True),
            NestedField(11, "source_method", StringType(), required=True),
            NestedField(12, "load_date", DateType(), required=True),
        )
