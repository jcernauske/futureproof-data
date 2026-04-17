"""Tests for AnthropicEconomicIndexIngestor.

Covers schema sanity, SOC normalization, and — critically — the three
correctness invariants of the v2 flatten pipeline that silently
regressed in prior revisions:

  1. ``task_pct`` stays in 0-100 percent units (NOT multiplied by 100).
  2. Many-to-many task-to-SOC fan-out emits one Bronze row per (task,
     SOC) pair and splits ``pct / n_soc`` so the global 100% invariant
     holds after flatten.
  3. ``automation_pct`` / ``augmentation_pct`` follow Anthropic's v2
     methodology: automation = directive + feedback_loop;
     augmentation = task_iteration + validation + learning (learning
     contributes to augmentation, NOT automation).
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pytest

from raw.anthropic_economic_index_ingestor import (
    AnthropicEconomicIndexIngestor,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "anthropic_economic_index"


def _make_ingestor() -> AnthropicEconomicIndexIngestor:
    """Create an ingestor instance without the full framework init.

    BaseIngestor.__init__ requires a SourceConfig + DomainManifest,
    but schema/coercion tests don't need them; skip via __new__.
    """
    return AnthropicEconomicIndexIngestor.__new__(AnthropicEconomicIndexIngestor)


class TestSchema:
    """Schema sanity checks."""

    def test_get_schema_returns_iceberg_schema(self) -> None:
        from pyiceberg.schema import Schema

        schema = _make_ingestor().get_schema()
        assert isinstance(schema, Schema)

    def test_schema_has_grain_field(self) -> None:
        schema = _make_ingestor().get_schema()
        field_names = [f.name for f in schema.fields]
        assert "task_id" in field_names

    def test_schema_has_all_raw_fields(self) -> None:
        schema = _make_ingestor().get_schema()
        field_names = {f.name for f in schema.fields}
        expected = {
            "task_id", "task_statement", "soc_code", "soc_title",
            "task_pct", "automation_pct", "augmentation_pct",
            "source_release",
            "ingested_at", "source_url", "source_method", "load_date",
        }
        assert expected.issubset(field_names), (
            f"Missing fields: {expected - field_names}"
        )


class TestFixtureSmoke:
    """Fetch + flatten round-trip against committed fixtures."""

    def test_fetch_reads_three_csvs(self) -> None:
        ingestor = _make_ingestor()
        result = ingestor.fetch(
            {"anthropic": "Anthropic Economic Index"},
            method="hf_git_clone",
            dataset_root=str(FIXTURE_DIR),
        )
        payload = result["anthropic"]
        assert payload["task_pct_rows"], "task_pct_sample.csv is empty"
        assert payload["automation_rows"], "automation_sample.csv is empty"
        assert payload["task_statements_rows"], "task_mappings_sample.csv is empty"
        assert payload["source_method"] == "fixtures"

    def test_flatten_produces_rows(self) -> None:
        ingestor = _make_ingestor()
        fetched = ingestor.fetch(
            {"anthropic": "Anthropic Economic Index"},
            method="hf_git_clone",
            dataset_root=str(FIXTURE_DIR),
        )
        rows = ingestor.flatten(fetched["anthropic"], entity_id="anthropic")

        assert rows, "flatten produced no rows"
        # Every row has required grain + release
        for row in rows:
            assert row["task_id"]
            assert row["task_statement"]
            assert row["source_release"]
        # At least some rows joined to SOC
        soc_matched = sum(1 for r in rows if r["soc_code"])
        assert soc_matched > 0, "expected at least one SOC-matched row"

    def test_flatten_task_pct_is_0_to_100(self) -> None:
        ingestor = _make_ingestor()
        fetched = ingestor.fetch(
            {"anthropic": "Anthropic Economic Index"},
            method="hf_git_clone",
            dataset_root=str(FIXTURE_DIR),
        )
        rows = ingestor.flatten(fetched["anthropic"], entity_id="anthropic")
        for row in rows:
            pct = row["task_pct"]
            if pct is not None:
                assert 0 <= pct <= 100, f"task_pct {pct} out of range"


class TestSocNormalization:
    """O*NET-SOC (XX-XXXX.XX) -> SOC (XX-XXXX) truncation and strict validation."""

    def test_strips_onet_overlay_suffix(self) -> None:
        normalize = AnthropicEconomicIndexIngestor._normalize_onet_soc
        assert normalize("15-1252.00") == "15-1252"
        assert normalize("15-1252.01") == "15-1252"

    def test_preserves_already_normalized(self) -> None:
        normalize = AnthropicEconomicIndexIngestor._normalize_onet_soc
        assert normalize("15-1252") == "15-1252"

    def test_handles_empty_and_none(self) -> None:
        normalize = AnthropicEconomicIndexIngestor._normalize_onet_soc
        assert normalize(None) is None
        assert normalize("") is None
        assert normalize("   ") is None

    def test_dashless_6_digits_recovered(self) -> None:
        """Chaos-monkey P1 fix: '151252' is unambiguous -> '15-1252'."""
        normalize = AnthropicEconomicIndexIngestor._normalize_onet_soc
        assert normalize("151252") == "15-1252"
        # And with an O*NET suffix attached
        assert normalize("151252.00") == "15-1252"

    def test_dashless_5_digits_rejected(self) -> None:
        """Ambiguous length (5) cannot be safely dash-inserted."""
        normalize = AnthropicEconomicIndexIngestor._normalize_onet_soc
        assert normalize("15125") is None

    def test_dashless_7_digits_rejected(self) -> None:
        """Ambiguous length (7) cannot be safely dash-inserted."""
        normalize = AnthropicEconomicIndexIngestor._normalize_onet_soc
        assert normalize("1512522") is None

    def test_wrong_dash_shape_rejected(self) -> None:
        """Dash in the wrong place is rejected rather than reshaped."""
        normalize = AnthropicEconomicIndexIngestor._normalize_onet_soc
        # Too few digits after the dash
        assert normalize("15-125") is None
        # Too many digits after the dash (pre-suffix split handles 7-char,
        # but longer suffixes don't match and are rejected)
        assert normalize("15-12522") is None
        # Dash too early
        assert normalize("1-51252") is None

    def test_letters_and_whitespace_rejected(self) -> None:
        """Non-numeric content or embedded whitespace -> None."""
        normalize = AnthropicEconomicIndexIngestor._normalize_onet_soc
        assert normalize("ABC-1252") is None
        assert normalize("15 1252") is None
        assert normalize("15_1252") is None

    def test_sentinel_strings_rejected(self) -> None:
        """'nan', 'none', 'null' (any case) -> None."""
        normalize = AnthropicEconomicIndexIngestor._normalize_onet_soc
        assert normalize("nan") is None
        assert normalize("NaN") is None
        assert normalize("None") is None
        assert normalize("NULL") is None


class TestMalformedSocDropped:
    """Chaos-monkey P1 scenario: malformed SOCs are dropped, not emitted as NULL rows.

    Design choice documented in `_normalize_onet_soc` docstring:
    when a real task's every SOC mapping is malformed, the entire task
    is dropped rather than emitting an extra NULL-SOC row (which would
    violate RAW-AEI-017's "exactly one NULL-SOC row" invariant).
    """

    @staticmethod
    def _build_fixture(tmp_path: Path, bad_soc: str) -> Path:
        """Build a minimal fixture dir where one task's only SOC is malformed."""
        fixture = tmp_path / "aei_fixtures"
        fixture.mkdir()
        # Task with a good SOC match and one with only a malformed SOC.
        (fixture / "task_pct_v2.csv").write_text(
            "task_name,pct\n"
            "write code.,50.0\n"
            "orphan task with bad soc.,30.0\n"
            "none,20.0\n"
        )
        (fixture / "automation_vs_augmentation_by_task.csv").write_text(
            "task_name,feedback_loop,directive,task_iteration,"
            "validation,learning,filtered\n"
            "write code.,0.10,0.20,0.50,0.15,0.05,0.00\n"
            "orphan task with bad soc.,0.10,0.20,0.50,0.15,0.05,0.00\n"
        )
        # task_statements: "write code" has a good SOC, the orphan
        # task_statement has only a malformed SOC.
        (fixture / "onet_task_statements.csv").write_text(
            "O*NET-SOC Code,Title,Task ID,Task,Task Type,"
            "Incumbents Responding,Date,Domain Source\n"
            "15-1252.00,Software Developers,1,write code.,Core,100,07/2023,Incumbent\n"
            f"{bad_soc},Orphan Occupation,2,orphan task with bad soc.,"
            "Core,100,07/2023,Incumbent\n"
        )
        return fixture

    def test_task_with_only_unrecoverable_malformed_soc_is_dropped(
        self, tmp_path: Path
    ) -> None:
        """No Bronze row is emitted for a task whose only SOC is unrecoverable.

        Uses '15-125' (dash present, wrong shape -- NOT recovered by
        the 6-digit heuristic). The good task still emits a row; the
        'none' placeholder is kept as the single expected NULL-SOC row;
        the orphan task is dropped.
        """
        fixture = self._build_fixture(tmp_path, bad_soc="15-125")
        ingestor = _make_ingestor()
        fetched = ingestor.fetch(
            {"anthropic": "Anthropic Economic Index"},
            method="hf_git_clone",
            dataset_root=str(fixture),
        )
        rows = ingestor.flatten(fetched["anthropic"], entity_id="anthropic")

        task_statements = [r["task_statement"] for r in rows]
        assert "orphan task with bad soc." not in task_statements, (
            "Task with only a malformed SOC should have been dropped, "
            f"but got rows: {rows}"
        )
        # The good task and the 'none' placeholder are still emitted
        assert "write code." in task_statements
        assert "none" in task_statements

    def test_dashless_6_digit_soc_is_recovered_not_dropped(
        self, tmp_path: Path
    ) -> None:
        """'151252' is unambiguous -- it IS recovered, not dropped.

        The spec allows heuristic dash-insertion when unambiguous. This
        test exists to document the recovery path (contrast with the
        unrecoverable cases which ARE dropped).
        """
        fixture = self._build_fixture(tmp_path, bad_soc="151252")
        ingestor = _make_ingestor()
        fetched = ingestor.fetch(
            {"anthropic": "Anthropic Economic Index"},
            method="hf_git_clone",
            dataset_root=str(fixture),
        )
        rows = ingestor.flatten(fetched["anthropic"], entity_id="anthropic")

        orphan_rows = [
            r for r in rows if r["task_statement"] == "orphan task with bad soc."
        ]
        assert len(orphan_rows) == 1
        # Recovered to canonical form
        assert orphan_rows[0]["soc_code"] == "15-1252"

    def test_malformed_soc_does_not_inflate_null_count(self, tmp_path: Path) -> None:
        """Exactly one NULL-SOC row (the 'none' placeholder) -- not two."""
        fixture = self._build_fixture(tmp_path, bad_soc="15-125")  # too few digits
        ingestor = _make_ingestor()
        fetched = ingestor.fetch(
            {"anthropic": "Anthropic Economic Index"},
            method="hf_git_clone",
            dataset_root=str(fixture),
        )
        rows = ingestor.flatten(fetched["anthropic"], entity_id="anthropic")

        null_soc_rows = [r for r in rows if r["soc_code"] is None]
        assert len(null_soc_rows) == 1, (
            f"Expected exactly 1 NULL-SOC row (the 'none' placeholder) but "
            f"got {len(null_soc_rows)}: {null_soc_rows}"
        )
        assert null_soc_rows[0]["task_statement"] == "none"

    def test_existing_good_socs_still_normalize(self, tmp_path: Path) -> None:
        """Regression guard: legitimate SOCs remain unchanged by the hardened normalizer."""
        # Re-use the main committed fixtures to confirm nothing regressed.
        ingestor = _make_ingestor()
        fetched = ingestor.fetch(
            {"anthropic": "Anthropic Economic Index"},
            method="hf_git_clone",
            dataset_root=str(FIXTURE_DIR),
        )
        rows = ingestor.flatten(fetched["anthropic"], entity_id="anthropic")
        # Every non-null soc_code must match the canonical regex
        import re

        soc_re = re.compile(r"^\d{2}-\d{4}$")
        for row in rows:
            if row["soc_code"] is not None:
                assert soc_re.match(row["soc_code"]), (
                    f"Bronze row has malformed SOC {row['soc_code']!r}"
                )
        # And we still see at least one SOC-matched row
        assert sum(1 for r in rows if r["soc_code"] is not None) > 0


class TestHeaderFastFail:
    """Chaos-monkey P2 Gap 2: missing required columns must fail fast at fetch()."""

    @staticmethod
    def _copy_fixtures_to(tmp_path: Path) -> Path:
        """Copy the committed fixtures to a writable temp dir."""
        dest = tmp_path / "aei_fixtures"
        shutil.copytree(FIXTURE_DIR, dest)
        return dest

    @staticmethod
    def _strip_column(csv_path: Path, column: str) -> None:
        """Rewrite a CSV in place with the given column removed."""
        with open(csv_path, newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
        header = rows[0]
        idx = header.index(column)
        new_rows = [r[:idx] + r[idx + 1 :] for r in rows]
        with open(csv_path, "w", newline="") as f:
            csv.writer(f).writerows(new_rows)

    def test_missing_column_in_task_pct_raises(self, tmp_path: Path) -> None:
        fixtures = self._copy_fixtures_to(tmp_path)
        # Drop the 'pct' column from task_pct_sample.csv
        self._strip_column(fixtures / "task_pct_sample.csv", "pct")

        ingestor = _make_ingestor()
        with pytest.raises(ValueError, match="missing required columns.*pct"):
            ingestor.fetch(
                {"anthropic": "Anthropic Economic Index"},
                method="hf_git_clone",
                dataset_root=str(fixtures),
            )

    def test_missing_column_in_automation_raises(self, tmp_path: Path) -> None:
        fixtures = self._copy_fixtures_to(tmp_path)
        self._strip_column(fixtures / "automation_sample.csv", "feedback_loop")

        ingestor = _make_ingestor()
        with pytest.raises(
            ValueError, match="missing required columns.*feedback_loop"
        ):
            ingestor.fetch(
                {"anthropic": "Anthropic Economic Index"},
                method="hf_git_clone",
                dataset_root=str(fixtures),
            )

    def test_missing_column_in_task_statements_raises(self, tmp_path: Path) -> None:
        fixtures = self._copy_fixtures_to(tmp_path)
        # Drop the SOC column -- no alias left either -> must raise.
        self._strip_column(fixtures / "task_mappings_sample.csv", "O*NET-SOC Code")

        ingestor = _make_ingestor()
        with pytest.raises(ValueError, match="task-statement columns"):
            ingestor.fetch(
                {"anthropic": "Anthropic Economic Index"},
                method="hf_git_clone",
                dataset_root=str(fixtures),
            )

    def test_header_check_runs_before_row_read(self, tmp_path: Path) -> None:
        """The error must be raised at the fetch() boundary, not via silent None-fill.

        Replace task_pct with a file that has a valid header row but a
        different column name, then confirm the error surfaces with
        the column-name message (not a generic parse error during
        the full-file read).
        """
        fixtures = self._copy_fixtures_to(tmp_path)
        (fixtures / "task_pct_sample.csv").write_text(
            "task_name,percentage\n"  # 'pct' renamed to 'percentage'
            "write code.,5.0\n"
        )
        ingestor = _make_ingestor()
        with pytest.raises(ValueError) as exc:
            ingestor.fetch(
                {"anthropic": "Anthropic Economic Index"},
                method="hf_git_clone",
                dataset_root=str(fixtures),
            )
        # Must call out the specific missing column name
        assert "pct" in str(exc.value)
        assert "missing required columns" in str(exc.value)


class TestCollapseAutomation:
    """v2 automation math — learning contributes to AUGMENTATION not automation."""

    def test_augmentation_includes_learning(self) -> None:
        """learning is user-learns-from-Claude => Claude assists => augmentation."""
        axes = {
            "directive": 0.10,
            "feedback_loop": 0.20,
            "task_iteration": 0.30,
            "validation": 0.10,
            "learning": 0.25,  # should land in augmentation
            "filtered": 0.05,
        }
        auto, aug = AnthropicEconomicIndexIngestor._collapse_automation(axes)
        assert auto == pytest.approx(30.0)  # (0.10 + 0.20) * 100
        assert aug == pytest.approx(65.0)  # (0.30 + 0.10 + 0.25) * 100

    def test_automation_plus_augmentation_plus_filtered_is_100(self) -> None:
        """Per-row invariant from Anthropic v2: 6 fields sum to 1.0."""
        axes = {
            "directive": 0.15,
            "feedback_loop": 0.10,
            "task_iteration": 0.30,
            "validation": 0.20,
            "learning": 0.15,
            "filtered": 0.10,
        }
        auto, aug = AnthropicEconomicIndexIngestor._collapse_automation(axes)
        filtered_pct = (axes["filtered"] or 0.0) * 100.0
        assert (auto + aug + filtered_pct) == pytest.approx(100.0)

    def test_fully_filtered_returns_none_none(self) -> None:
        axes = {
            "directive": 0.0, "feedback_loop": 0.0, "task_iteration": 0.0,
            "validation": 0.0, "learning": 0.0, "filtered": 1.0,
        }
        auto, aug = AnthropicEconomicIndexIngestor._collapse_automation(axes)
        assert auto is None and aug is None

    def test_none_input(self) -> None:
        assert AnthropicEconomicIndexIngestor._collapse_automation(None) == (None, None)


class TestGlobalShareInvariant:
    """Bronze flatten conserves the global 100% sum across fan-out.

    Covers bug fix #1 (no × 100 double-scaling) and bug fix #2
    (split pct / n_soc across multi-SOC tasks).
    """

    @staticmethod
    def _flatten() -> list[dict]:
        ingestor = _make_ingestor()
        fetched = ingestor.fetch(
            {"anthropic": "Anthropic Economic Index"},
            method="hf_git_clone",
            dataset_root=str(FIXTURE_DIR),
        )
        return ingestor.flatten(fetched["anthropic"], entity_id="anthropic")

    def test_sum_task_pct_matches_source(self) -> None:
        """SUM(task_pct) across Bronze rows equals sum of source pct column."""
        rows = self._flatten()
        total = sum(r["task_pct"] for r in rows if r["task_pct"] is not None)
        # Fixture source pct column sums to exactly 100.0
        assert total == pytest.approx(100.0, abs=0.01)

    def test_pct_stays_in_0_to_100_units(self) -> None:
        """Bug 1 regression: pct is already 0-100, do NOT × 100 again.

        Fixture source has a single task at 6.0% (visual design). If the
        old × 100 bug returned, that would become 600.0 which is out of
        range; even a single-SOC task would exceed 100.
        """
        rows = self._flatten()
        for row in rows:
            pct = row["task_pct"]
            if pct is not None:
                assert 0.0 <= pct <= 100.0, (
                    f"task_pct {pct} out of [0, 100] — did × 100 regress?"
                )

    def test_multi_soc_task_emits_multiple_rows(self) -> None:
        """Bug 2 regression: multi-SOC tasks emit one row per SOC."""
        rows = self._flatten()
        # "write documentation for new features." fixture task maps to
        # two distinct SOCs (15-1252 Software Developers, 27-3042
        # Technical Writers).
        docs = [
            r for r in rows
            if r["task_statement"] == "write documentation for new features."
        ]
        assert len(docs) == 2, (
            f"Expected 2 Bronze rows for multi-SOC fixture task, got {len(docs)}"
        )
        soc_codes = {r["soc_code"] for r in docs}
        assert soc_codes == {"15-1252", "27-3042"}

    def test_multi_soc_task_splits_pct_by_n_soc(self) -> None:
        """Bug 2: per-row task_pct = raw_pct / n_soc so global sum holds."""
        rows = self._flatten()
        docs = [
            r for r in rows
            if r["task_statement"] == "write documentation for new features."
        ]
        # Fixture raw pct = 2.0, fan-out = 2 → each Bronze row = 1.0
        for row in docs:
            assert row["task_pct"] == pytest.approx(1.0)
        # Sum across the fan-out reconstructs the source pct
        assert sum(r["task_pct"] for r in docs) == pytest.approx(2.0)

    def test_none_placeholder_kept_with_null_soc(self) -> None:
        """task_name='none' is kept in Bronze with null SOC (Silver excludes)."""
        rows = self._flatten()
        none_rows = [r for r in rows if r["task_statement"] == "none"]
        assert len(none_rows) == 1
        assert none_rows[0]["soc_code"] is None
        # Pct is NOT split for the none row (no fan-out)
        assert none_rows[0]["task_pct"] == pytest.approx(38.75)

    def test_grain_is_task_and_soc_composite(self) -> None:
        """Bug 2: grain is (task_id, soc_code) not just task_id."""
        rows = self._flatten()
        # Multi-SOC task shares a task_statement but the composite
        # (task_id, soc_code) must be unique across all Bronze rows.
        grains = [(r["task_id"], r["soc_code"]) for r in rows]
        assert len(grains) == len(set(grains))

    def test_automation_plus_augmentation_is_100_when_not_filtered(self) -> None:
        """Bug 3 regression: verify learning went into augmentation.

        For any fixture row with ``filtered=0``, automation + augmentation
        must equal 100 (6 axes sum to 1.0 => scaled to 100).
        """
        rows = self._flatten()
        # Use the orphan row which has filtered=0.0 in the fixture.
        orphan_rows = [
            r for r in rows if r["task_statement"] == "orphan task with no mapping row."
        ]
        assert orphan_rows, "fixture regression: orphan row missing"
        orphan = orphan_rows[0]
        assert orphan["automation_pct"] + orphan["augmentation_pct"] == pytest.approx(
            100.0
        )
        # Specific fixture axes: feedback_loop=0.10, directive=0.20,
        # task_iteration=0.50, validation=0.15, learning=0.05, filtered=0.0
        # v2: automation = (0.10+0.20)*100 = 30, augmentation = (0.50+0.15+0.05)*100 = 70
        assert orphan["automation_pct"] == pytest.approx(30.0)
        assert orphan["augmentation_pct"] == pytest.approx(70.0)

    def test_learning_contributes_to_augmentation_not_automation(self) -> None:
        """Regression guard: swap learning into automation and row would differ."""
        rows = self._flatten()
        orphan = next(
            r for r in rows
            if r["task_statement"] == "orphan task with no mapping row."
        )
        # If learning were (incorrectly) in automation, auto would be 35, aug 65.
        # The correct v2 split yields auto=30, aug=70. Assert both directions.
        assert orphan["automation_pct"] != pytest.approx(35.0), (
            "learning must NOT be added to automation (v2 methodology)"
        )
        assert orphan["augmentation_pct"] != pytest.approx(65.0)
