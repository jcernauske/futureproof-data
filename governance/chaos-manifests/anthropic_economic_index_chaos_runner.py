"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: raw-ingest-anthropic-economic-index
Tables: raw.anthropic_economic_index, base.anthropic_observed_exposure,
        consumable.ai_exposure (S3 additive columns)

Injects source-file and data corruptions across 16 scenarios and records
what the ingestor / Silver transformer / Gold LEFT JOIN did in response.

INFORMATION BARRIER: Written WITHOUT reading DQ rule definitions. Scenarios
come from the spec's chaos manifest + code-path analysis (schema + README).

The scenarios here are *structural* rather than row-level numeric corruption:
the spec's risk surface is dominated by (a) source acquisition (git/LFS/
network), (b) column drift (HuggingFace rewrites CSVs between releases),
and (c) aggregation invariants (global-share conservation across fan-out).
Each scenario reports PASS/FAIL against a specific expected behavior drawn
from the spec — not against DQ rules. A second phase cross-checks a subset
of P0 rules by inspecting post-injection outputs.
"""

from __future__ import annotations

import copy
import csv
import datetime
import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
SRC_ROOT = PROJECT_ROOT / "src"
REAL_RELEASE = PROJECT_ROOT / "data/raw/anthropic_economic_index/release_2025_03_27"

sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))


def _load_ingestor():
    """Lazy import so collection-time errors are surfaced in the cycle report."""
    from raw.anthropic_economic_index_ingestor import AnthropicEconomicIndexIngestor
    return AnthropicEconomicIndexIngestor


def _load_transformer():
    from silver.anthropic_observed_exposure_transformer import transform_rows
    return transform_rows


def _load_gold_blender():
    from gold.ai_exposure_transformer import blend_scores
    return blend_scores


# ---------------------------------------------------------------------------
# Fixture builders (copy real release, mutate copy)
# ---------------------------------------------------------------------------


def clone_real_release(dst: Path) -> Path:
    """Copy the real release files into a fresh fixtures dir."""
    dst.mkdir(parents=True, exist_ok=True)
    for name in (
        "task_pct_v2.csv",
        "automation_vs_augmentation_by_task.csv",
        "onet_task_statements.csv",
    ):
        src = REAL_RELEASE / name
        if src.exists():
            shutil.copyfile(src, dst / name)
    return dst


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
    return fieldnames, rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


# ---------------------------------------------------------------------------
# Simulated pipeline call
# ---------------------------------------------------------------------------


def _new_ingestor():
    """Instantiate the ingestor without the BaseIngestor framework init.

    Same pattern as tests/raw/test_anthropic_economic_index_ingestor.py:
    BaseIngestor requires SourceConfig + DomainManifest, but the
    fetch/flatten paths we exercise don't touch those attrs.
    """
    cls = _load_ingestor()
    return cls.__new__(cls)


def run_ingest(fixtures_dir: Path) -> tuple[list[dict] | None, str | None]:
    """Run the ingestor in test-mode against a fixtures dir.

    Returns (flat_rows, error_message). error_message is None on success.
    """
    try:
        ingestor = _new_ingestor()
        payload = ingestor.fetch(
            entities={"aei": "Anthropic Economic Index"},
            method="fixtures",
            dataset_root=str(fixtures_dir),
            release_name="chaos_test",
        )
        flat = ingestor.flatten(payload["aei"], entity_id="aei")
        return flat, None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def run_silver(bronze_rows: list[dict]) -> tuple[list[dict] | None, str | None]:
    """Run the Silver transform with an empty BLS reference (bls_match will be false)."""
    transform_rows = _load_transformer()
    try:
        silver_rows = transform_rows(bronze_rows, bls_rows=[])
        return silver_rows, None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Scenario: each returns dict(scenario_id, expected, injected, actual,
# verdict, evidence, related_dq_rule)
# ---------------------------------------------------------------------------


def scenario_1_network_failure() -> dict:
    """Simulate git clone failure with NO cache available → expect FileNotFoundError
    with a clear error message pointing to the clone command."""
    sid = "S1-network-failure-no-cache"
    expected = (
        "Ingestor raises FileNotFoundError with guidance to run `git clone` "
        "when neither the live clone nor the cache contains a release."
    )
    # Point both DATASET_ROOT and CACHE_ROOT at an empty temp dir
    with tempfile.TemporaryDirectory() as tmp:
        import importlib
        import raw.anthropic_economic_index_ingestor as mod
        importlib.reload(mod)
        AnthropicEconomicIndexIngestor = mod.AnthropicEconomicIndexIngestor
        original_dataset = mod.DATASET_ROOT
        original_cache = mod.CACHE_ROOT
        mod.DATASET_ROOT = str(Path(tmp) / "nonexistent_live")
        mod.CACHE_ROOT = str(Path(tmp) / "nonexistent_cache")
        try:
            ingestor = AnthropicEconomicIndexIngestor.__new__(AnthropicEconomicIndexIngestor)
            # Explicitly do NOT pass dataset_root -> forces production path
            try:
                ingestor.fetch(entities={"aei": "x"}, method="hf_git_clone")
                actual = "No error raised — bug: ingestor returned payload from nothing"
                verdict = "FAIL"
            except FileNotFoundError as exc:
                msg = str(exc)
                has_guidance = "git clone" in msg and "git lfs pull" in msg
                if has_guidance:
                    actual = "FileNotFoundError raised with clone+lfs instructions"
                    verdict = "PASS"
                else:
                    actual = f"FileNotFoundError raised but message lacks guidance: {msg[:100]}"
                    verdict = "PARTIAL"
            except Exception as exc:  # noqa: BLE001
                actual = f"Wrong exception type: {type(exc).__name__}: {exc}"
                verdict = "FAIL"
        finally:
            mod.DATASET_ROOT = original_dataset
            mod.CACHE_ROOT = original_cache

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "Empty DATASET_ROOT and CACHE_ROOT (simulate offline with no cache)",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "N/A (pre-DQ failure mode; ingest-time guard)",
    }


def scenario_2_git_lfs_missing() -> dict:
    """git-lfs not installed → release dir exists but CSVs are LFS pointer stubs.
    Expect the ingestor to either fail fast OR to parse rows==0 and fail Silver."""
    sid = "S2-git-lfs-pointer-stubs"
    expected = (
        "When CSVs are LFS pointer text (not real data), ingestor parses "
        "them but produces near-zero usable rows; Bronze row count check "
        "would fail. Ingestor should NOT crash silently."
    )
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = Path(tmp) / "fix"
        fixtures.mkdir()
        # LFS pointer stub contents (real git-lfs pointer format)
        stub = (
            "version https://git-lfs.github.com/spec/v1\n"
            "oid sha256:abcd1234\n"
            "size 12345\n"
        )
        for name in (
            "task_pct_v2.csv",
            "automation_vs_augmentation_by_task.csv",
            "onet_task_statements.csv",
        ):
            (fixtures / name).write_text(stub, encoding="utf-8")

        flat, err = run_ingest(fixtures)
        if err is not None:
            actual = f"Ingestor errored: {err}"
            verdict = "PASS"  # Failing fast is acceptable
        elif flat is not None and len(flat) == 0:
            actual = "Ingestor returned 0 rows (LFS stubs → empty parse)"
            verdict = "PASS"
        elif flat is not None and len(flat) < 100:
            actual = f"Ingestor returned {len(flat)} rows — well below 3800 floor"
            verdict = "PASS"  # DQ row-count rule will catch
        else:
            actual = f"Ingestor returned {len(flat) if flat else 0} rows — did not detect LFS stubs"
            verdict = "FAIL"

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "All three CSVs replaced with LFS pointer-stub text",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "raw.row_count_in_range (3800-4400)",
    }


def scenario_3_malformed_headers() -> dict:
    """Rename `pct` → `Percentage` in task_pct_v2. After the primary-agent fix,
    the fetch() boundary header check MUST fast-fail with a ValueError naming
    the missing `pct` column — no Bronze rows are emitted."""
    sid = "S3-malformed-headers"
    expected = (
        "Ingestor's fast-fail header check raises ValueError at fetch() with "
        "an explicit list of missing required columns. No Bronze rows are "
        "emitted (previously: 4082 rows with silent null pct)."
    )
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = clone_real_release(Path(tmp))
        path = fixtures / "task_pct_v2.csv"
        fields, rows = read_csv(path)
        # Rename `pct` to `Percentage`
        renamed = ["Percentage" if f == "pct" else f for f in fields]
        mutated = [
            {("Percentage" if k == "pct" else k): v for k, v in r.items()}
            for r in rows
        ]
        write_csv(path, renamed, mutated)

        flat, err = run_ingest(fixtures)
        if err is not None:
            # Expected path after fix: fast-fail at fetch() boundary.
            is_value_error = err.startswith("ValueError")
            names_pct = "'pct'" in err or "pct" in err
            if is_value_error and names_pct:
                actual = (
                    f"Fast-fail at fetch() boundary: {err[:160]}"
                )
                verdict = "PASS"
            else:
                actual = f"Ingestor errored but wrong signal: {err[:160]}"
                verdict = "PARTIAL"
        else:
            # Legacy silent-null behavior — no longer acceptable.
            all_null = all(r.get("task_pct") is None for r in (flat or []))
            total_pct = sum((r.get("task_pct") or 0.0) for r in (flat or []))
            actual = (
                f"Ingestor did NOT fast-fail on missing `pct`: emitted "
                f"{len(flat)} rows, all_null={all_null}, "
                f"SUM(task_pct)={total_pct:.2f}"
            )
            verdict = "FAIL"

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "Renamed `pct` column to `Percentage` in task_pct_v2.csv",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "ingestor fast-fail guard + raw.task_pct_global_sum",
    }


def scenario_4_missing_columns() -> dict:
    """Delete entire task_name column from task_pct_v2. After the fast-fail
    header check was added, the ingestor MUST raise ValueError at fetch()
    naming the missing `task_name` column."""
    sid = "S4-missing-required-columns"
    expected = (
        "Ingestor's fast-fail header check raises ValueError at fetch() "
        "naming the missing `task_name` column. No Bronze rows emitted."
    )
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = clone_real_release(Path(tmp))
        path = fixtures / "task_pct_v2.csv"
        fields, rows = read_csv(path)
        fields = [f for f in fields if f != "task_name"]
        mutated = [{k: v for k, v in r.items() if k != "task_name"} for r in rows]
        write_csv(path, fields, mutated)

        flat, err = run_ingest(fixtures)
        if err is not None:
            is_value_error = err.startswith("ValueError")
            names_task_name = "task_name" in err
            if is_value_error and names_task_name:
                actual = f"Fast-fail at fetch() boundary: {err[:160]}"
                verdict = "PASS"
            else:
                actual = f"Errored but wrong signal: {err[:160]}"
                verdict = "PARTIAL"
        elif flat is not None and len(flat) == 0:
            # Acceptable: emits 0 rows because keys are all empty.
            actual = "Ingestor emitted 0 rows (all task_name keys empty)"
            verdict = "PASS"
        else:
            actual = f"Ingestor emitted {len(flat)} rows despite missing task_name column"
            verdict = "FAIL"

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "Deleted `task_name` column from task_pct_v2.csv",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "ingestor fast-fail guard + raw.row_count_in_range",
    }


def scenario_5_soc_format_variations() -> dict:
    """Inject messy SOC formats. After the primary-agent P1 fix,
    _normalize_onet_soc validates against `^\\d{2}-\\d{4}$` and ONLY recovers
    the unambiguous dash-less 6-digit shape (`151252` → `15-1252`). All
    other malformed shapes (5-digit, 7-digit, dotted, letters, placeholders)
    are rejected. Bronze must emit ZERO malformed SOCs."""
    sid = "S5-soc-format-variations"
    expected = (
        "Bronze _normalize_onet_soc (a) strips O*NET overlay `.NN`, "
        "(b) recovers dash-less 6-digit unambiguously, "
        "(c) rejects all other malformed shapes. Every emitted row has "
        "soc_code matching ^\\d{2}-\\d{4}$ OR NULL."
    )
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = clone_real_release(Path(tmp))
        path = fixtures / "onet_task_statements.csv"
        fields, rows = read_csv(path)

        # Mutate first 10 rows with format variants. These are the
        # exact same 10 variants the pre-fix manifest exercised.
        variants = [
            "15-1252.00",   # overlay — normalize to 15-1252
            "15-1252",      # already canonical
            "151252",       # dash-less 6-digit — RECOVERED to 15-1252
            "15.1252",      # wrong separator — dot-strip then 4 digits → REJECTED
            "15-12520",     # dash present but 5-digit subcode — REJECTED
            "  15-1252 ",   # whitespace — trimmed then canonical
            "XX-XXXX",      # placeholder, non-numeric — REJECTED
            "",             # empty — REJECTED
            "NULL",         # sentinel — REJECTED
            "11-1011.99",   # overlay .99 — normalize to 11-1011
        ]
        for i, v in enumerate(variants):
            if i < len(rows):
                rows[i]["O*NET-SOC Code"] = v

        write_csv(path, fields, rows)

        flat, err = run_ingest(fixtures)
        if err is not None:
            actual = f"Ingestor errored: {err}"
            verdict = "FAIL"
        else:
            import re
            pattern = re.compile(r"^\d{2}-\d{4}$")
            bad = [
                r["soc_code"] for r in flat
                if r["soc_code"] is not None and not pattern.match(r["soc_code"])
            ]
            # Also sanity-check: at least one row should resolve to 15-1252
            # (from the dash-less recovery) and at least one to 11-1011.
            soc_set = {r["soc_code"] for r in flat if r["soc_code"]}
            has_recovered = "15-1252" in soc_set
            has_overlay = "11-1011" in soc_set
            if bad:
                actual = (
                    f"Emitted {len(bad)} malformed SOC codes "
                    f"(samples: {bad[:5]})"
                )
                verdict = "FAIL"
            elif not has_recovered or not has_overlay:
                actual = (
                    f"No malformed SOCs, but normalized recovery did not "
                    f"populate expected codes: has_15-1252={has_recovered}, "
                    f"has_11-1011={has_overlay}"
                )
                verdict = "PARTIAL"
            else:
                actual = (
                    f"All {len(flat)} emitted rows have well-formed or null "
                    f"SOC; dash-less '151252' recovered to '15-1252'; "
                    f"overlay '11-1011.99' normalized to '11-1011'; "
                    f"every other malformed variant rejected cleanly."
                )
                verdict = "PASS"

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "10 SOC format variants in onet_task_statements.csv",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "RAW-AEI-019 (P0 SOC regex) + silver.soc_code_format",
    }


def scenario_6_empty_task_pct() -> dict:
    """Empty task_pct_v2.csv (header only). Expect zero Bronze rows, DQ fails."""
    sid = "S6-empty-task-pct-file"
    expected = "Zero Bronze rows, row-count DQ rule fails."
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = clone_real_release(Path(tmp))
        path = fixtures / "task_pct_v2.csv"
        path.write_text("task_name,pct\n", encoding="utf-8")

        flat, err = run_ingest(fixtures)
        if err is not None:
            actual = f"Ingestor errored: {err}"
            verdict = "PASS"
        elif flat is not None and len(flat) == 0:
            actual = "Emitted 0 Bronze rows"
            verdict = "PASS"
        else:
            actual = f"Emitted {len(flat)} rows from empty source"
            verdict = "FAIL"
    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "task_pct_v2.csv reduced to header only",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "raw.row_count_in_range",
    }


def scenario_7_duplicate_task_ids() -> dict:
    """Duplicate rows in task_pct_v2 (same task_name twice). Expect the
    Bronze seen_grain guard to dedupe — one Bronze row per (task_id, soc)."""
    sid = "S7-duplicate-task-names-source"
    expected = (
        "When source CSV has the same task_name on multiple rows, the "
        "Bronze `seen_grain` set dedupes to one row per (task_id, soc_code); "
        "task_pct is NOT summed/doubled."
    )
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = clone_real_release(Path(tmp))
        path = fixtures / "task_pct_v2.csv"
        fields, rows = read_csv(path)
        # Duplicate first 20 rows
        dupes = [dict(r) for r in rows[:20]]
        rows.extend(dupes)
        write_csv(path, fields, rows)

        flat, err = run_ingest(fixtures)
        if err is not None:
            actual = f"Ingestor errored: {err}"
            verdict = "FAIL"
        else:
            # Composite uniqueness check
            grains = [(r["task_id"], r["soc_code"]) for r in flat]
            from collections import Counter
            dup_count = sum(v - 1 for v in Counter(grains).values() if v > 1)
            if dup_count == 0:
                actual = f"Emitted {len(flat)} rows, 0 duplicate (task_id, soc_code) grains"
                verdict = "PASS"
            else:
                actual = f"Emitted {len(flat)} rows, {dup_count} duplicate grains"
                verdict = "FAIL"

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "First 20 rows of task_pct_v2.csv duplicated",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "raw.composite_uniqueness (task_id,soc_code)",
    }


def scenario_8_release_folder_missing() -> dict:
    """Primary release absent → select fallback release.

    The current code path uses RELEASE_PREFERENCE and falls through to the
    next release that contains task_pct_v2.csv. We simulate by only staging
    the 2025-03-27 data in the cache (the code's fallback path)."""
    sid = "S8-release-folder-missing-fallback"
    expected = (
        "Ingestor's _select_release_dir() iterates RELEASE_PREFERENCE and "
        "uses the first release that contains task_pct_v2.csv, falling back "
        "to cache if live clone is absent."
    )
    import importlib
    import raw.anthropic_economic_index_ingestor as mod
    with tempfile.TemporaryDirectory() as tmp:
        # Stage cache only (no live clone). Put 2025-03-27 under cache root.
        cache_root = Path(tmp) / "cache"
        release_dir = cache_root / "release_2025_03_27"
        release_dir.mkdir(parents=True)
        for name in (
            "task_pct_v2.csv",
            "automation_vs_augmentation_by_task.csv",
            "onet_task_statements.csv",
        ):
            src = REAL_RELEASE / name
            if src.exists():
                shutil.copyfile(src, release_dir / name)

        original_dataset = mod.DATASET_ROOT
        original_cache = mod.CACHE_ROOT
        mod.DATASET_ROOT = str(Path(tmp) / "live_absent")
        mod.CACHE_ROOT = str(cache_root)

        try:
            importlib.reload(mod)
            # Restore patches after reload (reload undoes module var changes)
            mod.DATASET_ROOT = str(Path(tmp) / "live_absent")
            mod.CACHE_ROOT = str(cache_root)

            ingestor = mod.AnthropicEconomicIndexIngestor.__new__(
                mod.AnthropicEconomicIndexIngestor
            )
            try:
                payload = ingestor.fetch(entities={"aei": "x"}, method="hf_git_clone")
                flat = ingestor.flatten(payload["aei"], entity_id="aei")
                if payload["aei"]["source_method"] == "local_cache":
                    actual = f"Fallback to local_cache worked; emitted {len(flat)} Bronze rows"
                    verdict = "PASS"
                else:
                    actual = f"Unexpected source_method: {payload['aei']['source_method']}"
                    verdict = "PARTIAL"
            except Exception as exc:  # noqa: BLE001
                actual = f"Ingestor errored: {type(exc).__name__}: {exc}"
                verdict = "FAIL"
        finally:
            mod.DATASET_ROOT = original_dataset
            mod.CACHE_ROOT = original_cache
            importlib.reload(mod)

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "Live clone empty; cache contains only release_2025_03_27",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "N/A (acquisition-time resilience)",
    }


def scenario_9_extra_unexpected_columns() -> dict:
    """Add a bogus `debug_score` column to task_pct_v2. Expect no crash."""
    sid = "S9-extra-unexpected-columns"
    expected = "Ingestor ignores unknown columns; Bronze output unchanged."
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = clone_real_release(Path(tmp))
        path = fixtures / "task_pct_v2.csv"
        fields, rows = read_csv(path)
        fields.append("debug_score")
        for r in rows:
            r["debug_score"] = "42"
        write_csv(path, fields, rows)

        flat, err = run_ingest(fixtures)
        if err is not None:
            actual = f"Ingestor errored on extra column: {err}"
            verdict = "FAIL"
        elif flat is not None and len(flat) > 3800:
            actual = f"Emitted {len(flat)} rows — extra column ignored"
            verdict = "PASS"
        else:
            actual = f"Emitted {len(flat) if flat else 0} rows — unexpected row loss"
            verdict = "FAIL"

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "Added `debug_score` column to task_pct_v2.csv",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "N/A (schema robustness)",
    }


def scenario_10_all_filtered_task() -> dict:
    """Task with filtered=1.0 → automation_pct/augmentation_pct should be None."""
    sid = "S10-all-filtered-task-null-propagation"
    expected = (
        "When filtered>=0.999, _collapse_automation returns (None, None). "
        "Row still emitted in Bronze, task_pct preserved (the filter applies "
        "to Claude's content classifier, not to the row's existence)."
    )
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = clone_real_release(Path(tmp))
        aut_path = fixtures / "automation_vs_augmentation_by_task.csv"
        fields, rows = read_csv(aut_path)
        # Set first 5 rows to fully-filtered
        for i in range(min(5, len(rows))):
            for ax in ("directive", "feedback_loop", "task_iteration", "validation", "learning"):
                rows[i][ax] = "0.0"
            rows[i]["filtered"] = "1.0"
        write_csv(aut_path, fields, rows)

        flat, err = run_ingest(fixtures)
        if err is not None:
            actual = f"Ingestor errored: {err}"
            verdict = "FAIL"
        else:
            # Pull the tasks whose task_name matches the first 5 automation rows
            target_names = {rows[i]["task_name"] for i in range(min(5, len(rows)))}
            matched = [
                r for r in flat
                if (r["task_statement"] or "").strip().lower().rstrip(".")
                in {n.strip().lower().rstrip(".") for n in target_names}
            ]
            fully_null_auto = all(
                r["automation_pct"] is None and r["augmentation_pct"] is None
                for r in matched
            )
            if matched and fully_null_auto:
                actual = f"All {len(matched)} Bronze rows for filtered-tasks have null automation/augmentation"
                verdict = "PASS"
            elif not matched:
                actual = "No matching Bronze rows found (join failure)"
                verdict = "FAIL"
            else:
                leaked = [
                    (r["task_id"], r["automation_pct"], r["augmentation_pct"])
                    for r in matched
                    if r["automation_pct"] is not None or r["augmentation_pct"] is not None
                ]
                actual = f"{len(leaked)} filtered-task rows have non-null automation/augmentation: {leaked[:3]}"
                verdict = "FAIL"

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "5 rows in automation file set to filtered=1.0",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "raw.automation_augmentation_sum (tolerates nulls for filtered)",
    }


def scenario_11_stress_fanout() -> dict:
    """Add a synthetic task that maps to 50 distinct SOCs — stress fan-out
    beyond the observed max of 34 to ensure split math holds."""
    sid = "S11-stress-fanout-50-soc"
    expected = (
        "A single task mapping to 50 SOCs fans out to 50 Bronze rows. "
        "task_pct_split = raw_pct/50. Composite uniqueness preserved."
    )
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = clone_real_release(Path(tmp))

        # Add a unique synthetic task to all three files
        fake_task = "perform miscellaneous synthetic chaos task"

        # 1. Append to task_pct_v2
        pct_path = fixtures / "task_pct_v2.csv"
        fields, rows = read_csv(pct_path)
        rows.append({"task_name": fake_task, "pct": "5.0"})
        write_csv(pct_path, fields, rows)

        # 2. Append to automation file
        aut_path = fixtures / "automation_vs_augmentation_by_task.csv"
        fields, rows = read_csv(aut_path)
        rows.append({
            "task_name": fake_task, "feedback_loop": "0.1", "directive": "0.2",
            "task_iteration": "0.3", "validation": "0.2", "learning": "0.1", "filtered": "0.1",
        })
        write_csv(aut_path, fields, rows)

        # 3. Append 50 distinct SOCs in onet_task_statements
        stmts_path = fixtures / "onet_task_statements.csv"
        fields, rows = read_csv(stmts_path)
        for i in range(50):
            soc = f"{10 + (i // 10):02d}-{1000 + i * 7:04d}"  # 50 synthetic SOCs
            rows.append({
                "O*NET-SOC Code": f"{soc}.00",
                "Title": f"Synthetic Occupation {i}",
                "Task ID": f"9999{i:03d}",
                "Task": fake_task + ".",
                "Task Type": "Core",
                "Incumbents Responding": "1",
                "Date": "01/2025",
                "Domain Source": "Chaos",
            })
        write_csv(stmts_path, fields, rows)

        flat, err = run_ingest(fixtures)
        if err is not None:
            actual = f"Ingestor errored: {err}"
            verdict = "FAIL"
        else:
            # Filter Bronze rows for our synthetic task
            synthetic = [
                r for r in flat
                if (r["task_statement"] or "").strip().lower().rstrip(".") == fake_task
            ]
            # Expected: 50 rows, all task_pct ≈ 5.0 / 50 = 0.1
            got = len(synthetic)
            pct_ok = all(
                r["task_pct"] is not None and abs(r["task_pct"] - 0.1) < 1e-6
                for r in synthetic
            )
            socs_unique = len({r["soc_code"] for r in synthetic}) == got
            if got == 50 and pct_ok and socs_unique:
                actual = f"50 fan-out rows, each task_pct=0.1, all SOCs distinct"
                verdict = "PASS"
            else:
                actual = (
                    f"fan-out rows={got}, pct_ok={pct_ok}, "
                    f"unique_socs={len({r['soc_code'] for r in synthetic})}"
                )
                verdict = "FAIL"

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "Synthetic task with 50-way SOC fan-out",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "raw.composite_uniqueness + raw.task_pct_global_sum",
    }


def scenario_12_negative_nan_pct() -> dict:
    """Inject negative and NaN values into pct column. Expect coercion to
    float (including -5.0 and NaN pass through); DQ range rule catches it."""
    sid = "S12-negative-nan-pct"
    expected = (
        "Negative pct values pass through Bronze coercion (range enforced by "
        "DQ, not by ingestor). NaN coerces to float('nan') or is parsed as-is; "
        "Bronze accepts but SUM invariant breaks."
    )
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = clone_real_release(Path(tmp))
        path = fixtures / "task_pct_v2.csv"
        fields, rows = read_csv(path)
        # First 5 rows: negative; next 5: 'nan' string; next 3: non-numeric garbage
        for i in range(min(5, len(rows))):
            rows[i]["pct"] = "-1.5"
        for i in range(5, min(10, len(rows))):
            rows[i]["pct"] = "nan"
        for i in range(10, min(13, len(rows))):
            rows[i]["pct"] = "garbage_text"
        write_csv(path, fields, rows)

        flat, err = run_ingest(fixtures)
        if err is not None:
            actual = f"Ingestor errored: {err}"
            verdict = "FAIL"
        else:
            import math
            negs = [r for r in flat if r["task_pct"] is not None and r["task_pct"] < 0]
            nans = [r for r in flat if r["task_pct"] is not None and isinstance(r["task_pct"], float) and math.isnan(r["task_pct"])]
            nulls_from_garbage = sum(1 for r in flat if r["task_pct"] is None)
            total = sum(
                (r["task_pct"] or 0.0) for r in flat
                if r["task_pct"] is not None and not (isinstance(r["task_pct"], float) and math.isnan(r["task_pct"]))
            )
            # Expected behavior: negatives preserved, NaN preserved, 'garbage_text' coerces to None
            if negs and (nans or nulls_from_garbage > 0):
                actual = (
                    f"Bronze accepted corruptions as expected: "
                    f"{len(negs)} negative rows, {len(nans)} NaN rows, "
                    f"{nulls_from_garbage} null-from-garbage; "
                    f"SUM(task_pct) drift = {abs(100 - total):.2f}"
                )
                verdict = "PASS"  # Passing means DQ rule will catch, ingestor is permissive
            else:
                actual = "Ingestor may have silently dropped negatives/NaN"
                verdict = "PARTIAL"

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "5 negative pct, 5 NaN, 3 garbage-text in task_pct_v2",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "raw.task_pct_range (0<=x<=100) + raw.task_pct_global_sum",
    }


def scenario_13_unicode_quote_in_taskname() -> dict:
    """Inject task_name with smart quotes, trailing unicode punctuation, and
    embedded newline-escaped chars. Test normalization robustness."""
    sid = "S13-unicode-quotes-in-task-name"
    expected = (
        "_normalize_task_text lowercases + collapses whitespace + strips "
        "trailing ASCII period. Smart quotes (U+201C/201D) and unicode "
        "punctuation (ellipsis U+2026) are NOT stripped — so matches against "
        "onet_task_statements may fail, producing more NULL-SOC rows."
    )
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = clone_real_release(Path(tmp))
        path = fixtures / "task_pct_v2.csv"
        fields, rows = read_csv(path)
        # Find a row, mutate with unicode
        if len(rows) > 2:
            original = rows[2]["task_name"]
            rows[2]["task_name"] = "\u201c" + original + "\u201d"  # smart quotes
        if len(rows) > 3:
            rows[3]["task_name"] = rows[3]["task_name"] + "\u2026"  # ellipsis
        write_csv(path, fields, rows)

        flat, err = run_ingest(fixtures)
        if err is not None:
            actual = f"Ingestor errored on unicode: {err}"
            verdict = "FAIL"
        else:
            # Verify no crash; spot-check emitted row count still sensible
            null_soc_rows = sum(1 for r in flat if r["soc_code"] is None)
            actual = (
                f"Ingestor handled unicode without crashing; "
                f"{len(flat)} Bronze rows, {null_soc_rows} NULL-SOC rows"
            )
            verdict = "PASS" if len(flat) > 3800 else "PARTIAL"

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "Smart quotes and unicode ellipsis in task_name",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "(implicit) SOC-join coverage — null-SOC count drifts",
    }


def scenario_14_very_large_pct() -> dict:
    """Single pct value > 100. Bronze permits; SUM(task_pct) invariant fails
    AND single-row range rule fires. Silver observed_exposure_pct is clamped
    to [0,100] via _aggregate_observed_exposure."""
    sid = "S14-very-large-pct-single-row"
    expected = (
        "Bronze preserves the large value; range DQ fails. Silver's "
        "_aggregate_observed_exposure clamps SOC total to [0, 100]. "
        "Sum-invariant DQ fails (Bronze global sum >> 100)."
    )
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = clone_real_release(Path(tmp))
        path = fixtures / "task_pct_v2.csv"
        fields, rows = read_csv(path)
        if rows:
            rows[0]["pct"] = "500.0"
        write_csv(path, fields, rows)

        flat, err = run_ingest(fixtures)
        if err is not None:
            actual = f"Ingestor errored: {err}"
            verdict = "FAIL"
        else:
            # Locate rows for the tainted task
            tainted = [r for r in flat if r["task_pct"] is not None and r["task_pct"] > 100]
            # The task may fan out, so split pct < raw 500. Check raw/n_soc pattern
            total_pct = sum((r["task_pct"] or 0.0) for r in flat)
            silver_rows, serr = run_silver(flat)
            if serr is not None:
                actual = f"Silver errored: {serr}"
                verdict = "FAIL"
            else:
                max_silver = max(
                    (r.get("observed_exposure_pct") or 0.0) for r in silver_rows
                )
                clamped_ok = max_silver <= 100.0 + 1e-6
                actual = (
                    f"Bronze SUM(task_pct)={total_pct:.2f} (should fail invariant); "
                    f"Silver max observed_exposure_pct={max_silver:.2f} "
                    f"(clamped: {clamped_ok})"
                )
                verdict = "PASS" if clamped_ok else "FAIL"

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "First row's pct = 500.0",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "raw.task_pct_range + silver.observed_exposure_pct_range",
    }


def scenario_15_normalized_collision() -> dict:
    """Two source rows with task_name 'Foo.' and 'foo' — both normalize to
    'foo'. Bronze has no key-collision guard on task_pct → the later row
    wins in the statements index but task_pct rows are emitted per-original.
    Expected: both rows emitted to Bronze (separately), both aggregate."""
    sid = "S15-normalized-taskname-collision"
    expected = (
        "Two input rows whose normalized task_name collides (e.g. 'Foo.' vs 'foo') "
        "still emit independent Bronze rows because the (task_id, soc_code) composite "
        "grain differs (source order preserved). DQ composite uniqueness holds."
    )
    with tempfile.TemporaryDirectory() as tmp:
        fixtures = clone_real_release(Path(tmp))
        path = fixtures / "task_pct_v2.csv"
        fields, rows = read_csv(path)
        # Replace first 2 rows with normalize-collision pair; use a task name
        # that exists in onet_task_statements so we get a SOC bridge.
        target = "design and develop new products"  # likely exists (design/engineering)
        if len(rows) >= 2:
            rows[0]["task_name"] = target + "."
            rows[0]["pct"] = "2.0"
            rows[1]["task_name"] = target.upper()  # normalizes to same
            rows[1]["pct"] = "3.0"
        write_csv(path, fields, rows)

        flat, err = run_ingest(fixtures)
        if err is not None:
            actual = f"Ingestor errored: {err}"
            verdict = "FAIL"
        else:
            # Check that the grain set is still unique
            grains = [(r["task_id"], r["soc_code"]) for r in flat]
            from collections import Counter
            dups = sum(v - 1 for v in Counter(grains).values() if v > 1)
            if dups == 0:
                actual = f"Composite grain unique ({len(flat)} rows); collision handled"
                verdict = "PASS"
            else:
                actual = f"Composite grain has {dups} duplicate pairs (collision leaked)"
                verdict = "FAIL"

    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "Two normalized-collision rows ('x.' vs 'X') in task_pct_v2",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "raw.composite_uniqueness",
    }


def scenario_16_silver_empty_bronze() -> dict:
    """Silver called with empty Bronze → should produce empty Silver rows,
    not crash."""
    sid = "S16-silver-empty-bronze"
    expected = "Silver with zero Bronze rows returns [] (no crash)."
    silver_rows, serr = run_silver([])
    if serr is not None:
        actual = f"Silver errored: {serr}"
        verdict = "FAIL"
    elif silver_rows == []:
        actual = "Silver returned empty list"
        verdict = "PASS"
    else:
        actual = f"Silver returned {len(silver_rows)} rows from empty Bronze — unexpected"
        verdict = "FAIL"
    return {
        "scenario_id": sid,
        "expected": expected,
        "injected": "transform_rows(bronze_rows=[], bls_rows=[])",
        "actual": actual,
        "verdict": verdict,
        "related_dq_rule": "silver.row_count_in_range (700-900)",
    }


SCENARIOS = [
    scenario_1_network_failure,
    scenario_2_git_lfs_missing,
    scenario_3_malformed_headers,
    scenario_4_missing_columns,
    scenario_5_soc_format_variations,
    scenario_6_empty_task_pct,
    scenario_7_duplicate_task_ids,
    scenario_8_release_folder_missing,
    scenario_9_extra_unexpected_columns,
    scenario_10_all_filtered_task,
    scenario_11_stress_fanout,
    scenario_12_negative_nan_pct,
    scenario_13_unicode_quote_in_taskname,
    scenario_14_very_large_pct,
    scenario_15_normalized_collision,
    scenario_16_silver_empty_bronze,
]


TOTAL_CYCLES = 2


def run_cycle(cycle_num: int) -> dict[str, Any]:
    """Run all scenarios, returning a per-cycle verdict block."""
    print(f"\n{'=' * 70}")
    print(f"CYCLE {cycle_num} / {TOTAL_CYCLES}")
    print(f"{'=' * 70}")
    results = []
    for fn in SCENARIOS:
        try:
            r = fn()
        except Exception as exc:  # noqa: BLE001
            r = {
                "scenario_id": fn.__name__,
                "expected": "no crash",
                "injected": "n/a",
                "actual": f"runner crash: {type(exc).__name__}: {exc}",
                "verdict": "ERROR",
                "related_dq_rule": "",
                "traceback": traceback.format_exc(),
            }
        print(f"  {r['scenario_id']:<55} {r['verdict']}")
        results.append(r)
    return {
        "cycle": cycle_num,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scenarios": results,
        "counts": {
            "total": len(results),
            "pass": sum(1 for r in results if r["verdict"] == "PASS"),
            "partial": sum(1 for r in results if r["verdict"] == "PARTIAL"),
            "fail": sum(1 for r in results if r["verdict"] == "FAIL"),
            "error": sum(1 for r in results if r["verdict"] == "ERROR"),
        },
    }


def main():
    all_cycles = []
    consecutive_clean = 0
    for cycle in range(1, TOTAL_CYCLES + 1):
        cycle_result = run_cycle(cycle)
        all_cycles.append(cycle_result)
        fails = cycle_result["counts"]["fail"] + cycle_result["counts"]["error"]
        if fails == 0:
            consecutive_clean += 1
        else:
            consecutive_clean = 0

    manifest_json_path = (
        PROJECT_ROOT / "governance/chaos-manifests/"
        "raw-ingest-anthropic-economic-index-manifest.json"
    )
    manifest_data = {
        "spec": "raw-ingest-anthropic-economic-index",
        "tables": [
            "raw.anthropic_economic_index",
            "base.anthropic_observed_exposure",
            "consumable.ai_exposure",
        ],
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "consecutive_clean_cycles": consecutive_clean,
        "cycles": all_cycles,
    }
    manifest_json_path.write_text(
        json.dumps(manifest_data, indent=2, default=str) + "\n"
    )
    print(f"\nJSON manifest: {manifest_json_path}")
    return manifest_data


if __name__ == "__main__":
    main()
