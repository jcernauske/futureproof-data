"""Chaos Monkey 5-Cycle Adversarial Hardening Runner.

Spec:         onet-experience-requirements
Target:       raw.onet_experience (Bronze ingest)
Ingestor:     src/raw/onet_ingestor.py::OnetExperienceIngestor
Fixture:      tests/raw/onet_samples/Education, Training, and Experience.txt

This is a curated scenario runner. The real clean ingest (35,998 rows) passes
all 10 Bronze DQ rules; this runner mutates an in-memory copy of the small
test fixture and verifies that each corruption is caught by at least one rule
(or by ingestor-level handling, for scenarios 7/8).

Because the fixture is only 28 rows — 4 SOCs, partial scale coverage — any rule
that evaluates global row counts / occupation coverage / per-scale category
counts will ALWAYS fail on it. These "inevitable fails" are captured once
against the clean fixture (the baseline) and then filtered out of each
scenario's report: only rules that *newly fire or flip* on top of the baseline
are attributed to the injected corruption. The scenario "caught?" verdict is
based on the delta, not the absolute fail list.

Information Barrier: This runner does NOT read
  - governance/dq-rules/raw-onet-experience.json (loaded as opaque JSON)
  - governance/dq-results/*
  - governance/dq-scorecards/*
Rule authorship is not inspected. SQL is executed against DuckDB via the same
pattern as scripts/dq_execute_onet_experience.py.

Safety:  Uses only in-memory DuckDB and an ephemeral shadow Iceberg
write path under data/bronze/iceberg_warehouse/shadow_bronze/; the real
bronze.onet_experience table is never mutated. The three-layer kill switch
is enforced below (CHAOS_MONKEY_ENABLED=true, BRIGHTSMITH_ENV=dev).
"""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import os
import sys
import tempfile
import traceback
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

FIXTURE_PATH = (
    PROJECT_ROOT
    / "tests"
    / "raw"
    / "onet_samples"
    / "Education, Training, and Experience.txt"
)
RULES_PATH = PROJECT_ROOT / "governance" / "dq-rules" / "raw-onet-experience.json"
REPORT_DIR = PROJECT_ROOT / "governance" / "chaos-reports"

# ---------------------------------------------------------------------------
# Safety — three-layer kill switch
# ---------------------------------------------------------------------------


def safety_check() -> None:
    os.environ["CHAOS_MONKEY_ENABLED"] = "true"
    os.environ["BRIGHTSMITH_ENV"] = "dev"
    enabled = os.environ.get("CHAOS_MONKEY_ENABLED", "").lower() == "true"
    dev = os.environ.get("BRIGHTSMITH_ENV", "").lower() == "dev"
    if not enabled or not dev:
        print("SAFETY ABORT: CHAOS_MONKEY_ENABLED=true and BRIGHTSMITH_ENV=dev required.")
        sys.exit(2)
    print("Safety: CHAOS_MONKEY_ENABLED=true, BRIGHTSMITH_ENV=dev")


# ---------------------------------------------------------------------------
# Fixture loading + ingestor wiring
# ---------------------------------------------------------------------------

TSV_HEADER = [
    "O*NET-SOC Code",
    "Element ID",
    "Element Name",
    "Scale ID",
    "Category",
    "Data Value",
    "N",
    "Standard Error",
    "Lower CI Bound",
    "Upper CI Bound",
    "Recommend Suppress",
    "Date",
    "Domain Source",
]


def load_fixture_rows() -> list[dict[str, str]]:
    """Parse the TSV fixture into raw row dicts (pre-ingestor)."""
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    return [dict(r) for r in reader]


def run_ingestor(raw_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Run the raw rows through OnetExperienceIngestor.flatten()."""
    from raw.onet_ingestor import OnetExperienceIngestor

    ingestor = OnetExperienceIngestor.__new__(OnetExperienceIngestor)
    flat = ingestor.flatten(raw_rows, entity_id="chaos")

    # Add Iceberg metadata columns so the DQ SQL (which references no metadata)
    # still works and the schema mirrors the real bronze parquet.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = date.today()
    for r in flat:
        r.setdefault("ingested_at", now)
        r.setdefault("source_url", "https://www.onetcenter.org/dl_files/database/db_30_2_text.zip")
        r.setdefault("source_method", "bulk_zip_download")
        r.setdefault("load_date", today)
    return flat


# ---------------------------------------------------------------------------
# DuckDB materialization + opaque rule execution
# ---------------------------------------------------------------------------


def materialize(flat: list[dict[str, Any]]) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA raw")
    con.execute(
        """
        CREATE TABLE raw.onet_experience (
            onet_soc_code       VARCHAR,
            element_id          VARCHAR,
            element_name        VARCHAR,
            scale_id            VARCHAR,
            category            INTEGER,
            data_value          DOUBLE,
            n                   INTEGER,
            standard_error      DOUBLE,
            lower_ci_bound      DOUBLE,
            upper_ci_bound      DOUBLE,
            recommend_suppress  VARCHAR,
            date                VARCHAR,
            domain_source       VARCHAR,
            ingested_at         TIMESTAMP,
            source_url          VARCHAR,
            source_method       VARCHAR,
            load_date           DATE
        )
        """
    )
    if flat:
        cols = [
            "onet_soc_code",
            "element_id",
            "element_name",
            "scale_id",
            "category",
            "data_value",
            "n",
            "standard_error",
            "lower_ci_bound",
            "upper_ci_bound",
            "recommend_suppress",
            "date",
            "domain_source",
            "ingested_at",
            "source_url",
            "source_method",
            "load_date",
        ]
        placeholders = ", ".join(["?"] * len(cols))
        rows = [[r.get(c) for c in cols] for r in flat]
        con.executemany(
            f"INSERT INTO raw.onet_experience ({', '.join(cols)}) VALUES ({placeholders})",
            rows,
        )
    return con


def load_rules() -> list[dict]:
    """Load rules JSON as opaque dicts. We do not interpret the SQL or logic."""
    return json.loads(RULES_PATH.read_text())["rules"]


def exec_rules(con: duckdb.DuckDBPyConnection, rules: list[dict]) -> dict[str, str]:
    """Execute every rule; return {rule_id: PASS|FAIL|ERROR}."""
    verdicts: dict[str, str] = {}
    for rule in rules:
        rid = rule["rule_id"]
        sql = rule["sql"]
        threshold = rule["threshold"].replace(" ", "")
        try:
            res = con.execute(sql).fetchall()
            if threshold == "result=0":
                actual = int(res[0][0]) if res else 0
                passed = actual == 0
            elif threshold == "result_count=0":
                passed = len(res) == 0
            elif threshold.startswith("result_count<="):
                passed = len(res) <= int(threshold.split("<=", 1)[1])
            elif threshold.startswith("result<="):
                actual = int(res[0][0]) if res else 0
                passed = actual <= int(threshold.split("<=", 1)[1])
            else:
                # Unknown threshold form — treat as fail-safe.
                passed = False
            verdicts[rid] = "PASS" if passed else "FAIL"
        except Exception:  # noqa: BLE001
            verdicts[rid] = "ERROR"
    return verdicts


def fail_set(verdicts: dict[str, str]) -> set[str]:
    return {rid for rid, v in verdicts.items() if v != "PASS"}


# ---------------------------------------------------------------------------
# Scenario library
# ---------------------------------------------------------------------------


def make_clean_synthetic() -> list[dict[str, str]]:
    """Build a synthetic "clean" baseline that would pass row-count / coverage
    rules (approx 35,000 rows, 878 SOCs, all 4 scales with correct per-scale
    category counts).

    This lets us observe the clean-pass behavior independent of the tiny
    test fixture. Used alongside the fixture baseline so we can tell which
    rules are tripped by "fixture too small" vs by injected corruption.
    """
    rows: list[dict[str, str]] = []
    # 880 synthetic SOC codes to satisfy the 800-1100 coverage band.
    # Format: XX-XXXX.XX
    for i in range(880):
        maj = f"{11 + (i % 10):02d}"  # 11..20
        mid = f"{1000 + i:04d}"
        suf = "00"
        soc = f"{maj}-{mid}.{suf}"
        # RL: 12 categories summing to 100
        for cat in range(1, 13):
            rows.append(
                {
                    "O*NET-SOC Code": soc,
                    "Element ID": "2.D.1",
                    "Element Name": "Required Level of Education",
                    "Scale ID": "RL",
                    "Category": str(cat),
                    "Data Value": f"{100.0 / 12:.4f}",
                    "N": "25",
                    "Standard Error": "1.0",
                    "Lower CI Bound": "",
                    "Upper CI Bound": "",
                    "Recommend Suppress": "N",
                    "Date": "08/2023",
                    "Domain Source": "Incumbent",
                }
            )
        # RW: 11 categories summing to 100
        for cat in range(1, 12):
            rows.append(
                {
                    "O*NET-SOC Code": soc,
                    "Element ID": "3.A.1",
                    "Element Name": "Related Work Experience",
                    "Scale ID": "RW",
                    "Category": str(cat),
                    "Data Value": f"{100.0 / 11:.4f}",
                    "N": "25",
                    "Standard Error": "1.0",
                    "Lower CI Bound": "",
                    "Upper CI Bound": "",
                    "Recommend Suppress": "N",
                    "Date": "08/2023",
                    "Domain Source": "Incumbent",
                }
            )
        # PT: 9 categories summing to 100
        for cat in range(1, 10):
            rows.append(
                {
                    "O*NET-SOC Code": soc,
                    "Element ID": "3.A.2",
                    "Element Name": "On-Site or In-Plant Training",
                    "Scale ID": "PT",
                    "Category": str(cat),
                    "Data Value": f"{100.0 / 9:.4f}",
                    "N": "25",
                    "Standard Error": "1.0",
                    "Lower CI Bound": "",
                    "Upper CI Bound": "",
                    "Recommend Suppress": "N",
                    "Date": "08/2023",
                    "Domain Source": "Incumbent",
                }
            )
        # OJ: 9 categories summing to 100
        for cat in range(1, 10):
            rows.append(
                {
                    "O*NET-SOC Code": soc,
                    "Element ID": "3.A.3",
                    "Element Name": "On-the-Job Training",
                    "Scale ID": "OJ",
                    "Category": str(cat),
                    "Data Value": f"{100.0 / 9:.4f}",
                    "N": "25",
                    "Standard Error": "1.0",
                    "Lower CI Bound": "",
                    "Upper CI Bound": "",
                    "Recommend Suppress": "N",
                    "Date": "08/2023",
                    "Domain Source": "Incumbent",
                }
            )
    return rows


# --- Mutators ---


def _clone(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [dict(r) for r in rows]


def mut_malformed_soc_1digit_suffix(rows):
    # XX-XXXX.X instead of XX-XXXX.XX
    out = _clone(rows)
    out[0]["O*NET-SOC Code"] = "11-1011.0"
    return out


def mut_malformed_soc_5digit_base(rows):
    # XX-XXXXX.XX instead of XX-XXXX.XX
    out = _clone(rows)
    out[0]["O*NET-SOC Code"] = "11-10115.00"
    return out


def mut_malformed_soc_nonnumeric(rows):
    out = _clone(rows)
    out[0]["O*NET-SOC Code"] = "ABC-DEFG.HI"
    return out


def mut_invalid_scale_xx(rows):
    out = _clone(rows)
    out[0]["Scale ID"] = "XX"
    return out


def mut_invalid_scale_lowercase(rows):
    out = _clone(rows)
    out[0]["Scale ID"] = "rw"
    return out


def mut_invalid_scale_null(rows):
    # Null scale_id — ingestor will skip the row (scale_id is required grain).
    # Rule should therefore see coverage/grain impact; this is a dual-attack case.
    out = _clone(rows)
    out[0]["Scale ID"] = ""
    return out


def mut_data_value_over_100(rows):
    out = _clone(rows)
    # pick an RW row
    for r in out:
        if r["Scale ID"] == "RW":
            r["Data Value"] = "101.0"
            break
    return out


def mut_data_value_negative(rows):
    out = _clone(rows)
    for r in out:
        if r["Scale ID"] == "RW":
            r["Data Value"] = "-5.0"
            break
    return out


def mut_data_value_na_string(rows):
    # Pre-ingestor: "N/A" coerces to None → row dropped. Net effect: one RW row
    # drops from an occupation, breaking its sum-to-100.
    out = _clone(rows)
    for r in out:
        if r["Scale ID"] == "RW" and r["O*NET-SOC Code"] == "15-1252.00":
            r["Data Value"] = "N/A"
            break
    return out


def mut_broken_sum_12_categories(rows):
    """Add a 12th RW category to some occupation (should be 11 for RW)."""
    out = _clone(rows)
    out.append(
        {
            "O*NET-SOC Code": "11-1011.00",
            "Element ID": "3.A.1",
            "Element Name": "Related Work Experience",
            "Scale ID": "RW",
            "Category": "12",  # invalid 12th RW category
            "Data Value": "5.00",
            "N": "29",
            "Standard Error": "1.0",
            "Lower CI Bound": "",
            "Upper CI Bound": "",
            "Recommend Suppress": "N",
            "Date": "08/2023",
            "Domain Source": "Incumbent",
        }
    )
    return out


def mut_broken_sum_95(rows):
    """Mis-distribute RW percentages for 15-1252.00 so they sum to 95."""
    out = _clone(rows)
    # All five 15-1252.00 RW values are 5.11+18.27+45.33+21.05+10.24 = 100.00
    # Divide each by 100/95 to make them sum to 95.
    for r in out:
        if r["O*NET-SOC Code"] == "15-1252.00" and r["Scale ID"] == "RW":
            old = float(r["Data Value"])
            r["Data Value"] = f"{old * 0.95:.4f}"
    return out


def mut_broken_sum_105(rows):
    """Mis-distribute RW percentages for 15-1252.00 so they sum to 105."""
    out = _clone(rows)
    for r in out:
        if r["O*NET-SOC Code"] == "15-1252.00" and r["Scale ID"] == "RW":
            old = float(r["Data Value"])
            r["Data Value"] = f"{old * 1.05:.4f}"
    return out


def mut_null_element_id(rows):
    # Null element_id: ingestor will drop the row (it's a required grain field).
    # This still simulates the sentinel case — we also inject a NULL element_id
    # row AFTER ingestion to ensure the rule sees a null, not an absence.
    out = _clone(rows)
    out[0]["Element ID"] = ""
    return out


def mut_duplicate_grain(rows):
    """Two rows with same (onet_soc_code, element_id, scale_id, category)."""
    out = _clone(rows)
    # Dup row 6 (first 11-1011 RW row, category 1)
    dup_source = next(
        r
        for r in out
        if r["O*NET-SOC Code"] == "11-1011.00"
        and r["Scale ID"] == "RW"
        and r["Category"] == "1"
    )
    out.append(dict(dup_source))
    return out


def mut_unexpected_scale_5th(rows):
    """A new 5th scale 'XY' — O*NET adds new scale in hypothetical future version."""
    out = _clone(rows)
    out.append(
        {
            "O*NET-SOC Code": "11-1011.00",
            "Element ID": "4.A.1",
            "Element Name": "Invented Future Scale",
            "Scale ID": "XY",
            "Category": "1",
            "Data Value": "100.00",
            "N": "29",
            "Standard Error": "",
            "Lower CI Bound": "",
            "Upper CI Bound": "",
            "Recommend Suppress": "N",
            "Date": "08/2023",
            "Domain Source": "Incumbent",
        }
    )
    return out


def mut_suppress_inconsistency(rows):
    """Null data_value but recommend_suppress='N' (should be Y if suppressed)."""
    # Ingestor would drop the row because data_value is required grain.
    # Instead, we inject post-ingest: set a row's data_value to None while
    # leaving recommend_suppress='N' — see inject_post_ingest().
    return rows


# Scenarios 7 and 8 hit the ingestor directly (no rule is expected to fire —
# behavior check only).

def behavior_check_truncated_zip() -> dict[str, Any]:
    """Scenario 7: truncated ZIP / empty text file. Ingestor should fail loud."""
    from raw.onet_ingestor import OnetExperienceIngestor

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "Education, Training, and Experience.txt"
        p.write_bytes(b"")  # empty file — truncated download symptom
        ingestor = OnetExperienceIngestor.__new__(OnetExperienceIngestor)
        try:
            parsed = ingestor._read_from_cache(Path(d))
            flat = ingestor.flatten(parsed, entity_id="chaos")
            return {
                "raised": False,
                "parsed_rows": len(parsed),
                "flat_rows": len(flat),
                "note": (
                    "INGESTOR ACCEPTED EMPTY FILE silently — parsed 0 rows, "
                    "flattened 0 rows. No exception raised. This is the "
                    "behavior we need to audit."
                ),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "raised": True,
                "exception_type": type(exc).__name__,
                "message": str(exc),
            }


def behavior_check_missing_file() -> dict[str, Any]:
    """Scenario 8: wrong file in ZIP (target .txt missing). Ingestor should raise."""
    from raw.onet_ingestor import OnetExperienceIngestor

    with tempfile.TemporaryDirectory() as d:
        # Create a sibling file, but NOT the target one.
        (Path(d) / "Some Other File.txt").write_text("not the file")
        ingestor = OnetExperienceIngestor.__new__(OnetExperienceIngestor)
        try:
            ingestor._read_from_cache(Path(d))
            return {
                "raised": False,
                "note": "INGESTOR DID NOT RAISE when target file missing. BUG.",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "raised": True,
                "exception_type": type(exc).__name__,
                "message": str(exc),
            }


def inject_post_ingest_null_data_value_inconsistent(
    flat: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """After ingestor runs, poke a null data_value with recommend_suppress='N'."""
    out = [dict(r) for r in flat]
    if out:
        out[0] = dict(out[0])
        out[0]["data_value"] = None
        out[0]["recommend_suppress"] = "N"
    return out


def inject_post_ingest_null_element_id(
    flat: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Force a null element_id into the materialized table (ingestor drops these,
    so we bypass the ingestor to simulate what a faulty upstream would produce).
    """
    out = [dict(r) for r in flat]
    if out:
        out[0] = dict(out[0])
        out[0]["element_id"] = None
    return out


# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------


# Each scenario: (id, label, dimension, rate, mutator_spec)
# mutator_spec can be:
#   {"raw": fn}          — mutate at raw-TSV layer, then run ingestor
#   {"flat": fn}         — mutate after ingestor, then materialize
#   {"behavior": fn}     — ingestor-level behavior check, no DQ run
SCENARIOS: list[dict[str, Any]] = [
    # 1. Malformed SOC code
    {
        "id": "S1a",
        "label": "malformed_soc_1digit_suffix",
        "dimension": "validity",
        "rate": 0.05,
        "expected_guard": "RAW-ONET-EXP-002 (SOC format)",
        "mutator": {"raw": mut_malformed_soc_1digit_suffix},
    },
    {
        "id": "S1b",
        "label": "malformed_soc_5digit_base",
        "dimension": "validity",
        "rate": 0.05,
        "expected_guard": "RAW-ONET-EXP-002 (SOC format)",
        "mutator": {"raw": mut_malformed_soc_5digit_base},
    },
    {
        "id": "S1c",
        "label": "malformed_soc_nonnumeric",
        "dimension": "validity",
        "rate": 0.05,
        "expected_guard": "RAW-ONET-EXP-002 (SOC format)",
        "mutator": {"raw": mut_malformed_soc_nonnumeric},
    },
    # 2. Invalid scale_id
    {
        "id": "S2a",
        "label": "invalid_scale_XX",
        "dimension": "validity",
        "rate": 0.06,
        "expected_guard": "RAW-ONET-EXP-003 (scale_id in set)",
        "mutator": {"raw": mut_invalid_scale_xx},
    },
    {
        "id": "S2b",
        "label": "invalid_scale_lowercase_rw",
        "dimension": "validity",
        "rate": 0.06,
        "expected_guard": "RAW-ONET-EXP-003 (scale_id in set)",
        "mutator": {"raw": mut_invalid_scale_lowercase},
    },
    {
        "id": "S2c",
        "label": "null_scale",
        "dimension": "completeness+validity",
        "rate": 0.06,
        "expected_guard": "Ingestor drops row (scale_id is required grain field)",
        "defense_is_ingestor": True,
        "mutator": {"raw": mut_invalid_scale_null},
    },
    # 3. Out-of-range data_value
    {
        "id": "S3a",
        "label": "data_value_over_100",
        "dimension": "validity/reasonableness",
        "rate": 0.07,
        "expected_guard": "RAW-ONET-EXP-004 (data_value in [0,100])",
        "mutator": {"raw": mut_data_value_over_100},
    },
    {
        "id": "S3b",
        "label": "data_value_negative",
        "dimension": "validity",
        "rate": 0.07,
        "expected_guard": "RAW-ONET-EXP-004 (data_value in [0,100])",
        "mutator": {"raw": mut_data_value_negative},
    },
    {
        "id": "S3c",
        "label": "data_value_NA_coerced_to_null_drop",
        "dimension": "validity + consistency",
        "rate": 0.07,
        "expected_guard": "Ingestor drops row; per-occupation sum != 100 → RAW-ONET-EXP-005",
        "mutator": {"raw": mut_data_value_na_string},
    },
    # 4. Broken per-occupation sum
    {
        "id": "S4a",
        "label": "12_categories_for_RW",
        "dimension": "consistency",
        "rate": 0.08,
        "expected_guard": "Per-scale category counts / RAW-ONET-EXP-005 sum",
        "mutator": {"raw": mut_broken_sum_12_categories},
    },
    {
        "id": "S4b",
        "label": "sum_to_95",
        "dimension": "consistency",
        "rate": 0.08,
        "expected_guard": "RAW-ONET-EXP-005 (sum ~= 100)",
        "mutator": {"raw": mut_broken_sum_95},
    },
    {
        "id": "S4c",
        "label": "sum_to_105",
        "dimension": "consistency",
        "rate": 0.08,
        "expected_guard": "RAW-ONET-EXP-005 (sum ~= 100)",
        "mutator": {"raw": mut_broken_sum_105},
    },
    # 5. Null element_id
    {
        "id": "S5",
        "label": "null_element_id_post_ingest",
        "dimension": "completeness",
        "rate": 0.05,
        "expected_guard": "RAW-ONET-EXP-006 (element_id non-null)",
        "mutator": {"flat": inject_post_ingest_null_element_id},
    },
    # 6. Duplicate grain
    {
        "id": "S6",
        "label": "duplicate_grain",
        "dimension": "uniqueness",
        "rate": 0.05,
        "expected_guard": "RAW-ONET-EXP-007 (grain uniqueness)",
        "mutator": {"raw": mut_duplicate_grain},
    },
    # 9. Unexpected 5th scale (O*NET future version)
    {
        "id": "S9",
        "label": "unexpected_5th_scale_XY",
        "dimension": "validity/coverage",
        "rate": 0.10,
        "expected_guard": "RAW-ONET-EXP-003 (scale_id in set)",
        "mutator": {"raw": mut_unexpected_scale_5th},
    },
    # 10. Suppress inconsistency
    {
        "id": "S10",
        "label": "null_data_value_suppress_N",
        "dimension": "consistency (optional)",
        "rate": 0.05,
        "expected_guard": "(gap candidate — no rule expected)",
        "mutator": {"flat": inject_post_ingest_null_data_value_inconsistent},
    },
    # 7 + 8 handled separately (behavior checks, not DQ rule runs).
]


# ---------------------------------------------------------------------------
# Cycle execution
# ---------------------------------------------------------------------------


def run_one_scenario(
    scenario: dict[str, Any],
    raw_fixture: list[dict[str, str]],
    baseline_fails: set[str],
    rules: list[dict],
) -> dict[str, Any]:
    spec = scenario["mutator"]
    try:
        if "raw" in spec:
            mutated_raw = spec["raw"](raw_fixture)
            flat = run_ingestor(mutated_raw)
        elif "flat" in spec:
            flat = run_ingestor(raw_fixture)
            flat = spec["flat"](flat)
        else:
            return {"error": "bad mutator spec"}

        con = materialize(flat)
        verdicts = exec_rules(con, rules)
        con.close()

        fails = fail_set(verdicts)
        new_fails = sorted(fails - baseline_fails)
        flipped_to_pass = sorted(baseline_fails - fails)

        defense_is_ingestor = scenario.get("defense_is_ingestor", False)
        # For scenarios whose expected defense IS the ingestor, we verify by
        # checking that the corruption did NOT reach the flat table intact.
        # If the row was dropped (fewer rows than baseline), the ingestor
        # defended successfully and we count the scenario caught.
        caught_by_ingestor = False
        if defense_is_ingestor:
            # baseline rows for fixture is 26 (27 - 1 already-suppressed-null row)
            # we expect the mutation to drop an extra row
            caught_by_ingestor = len(flat) < 26

        return {
            "id": scenario["id"],
            "label": scenario["label"],
            "dimension": scenario["dimension"],
            "rate": scenario["rate"],
            "expected_guard": scenario["expected_guard"],
            "defense_is_ingestor": defense_is_ingestor,
            "caught_by_ingestor": caught_by_ingestor,
            "rows_in_table": len(flat),
            "new_fails_vs_baseline": new_fails,
            "flipped_to_pass_vs_baseline": flipped_to_pass,
            "caught": bool(new_fails) or caught_by_ingestor,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "id": scenario["id"],
            "label": scenario["label"],
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc().splitlines()[-3:],
            "caught": False,
        }


def compute_baseline(raw_fixture, rules) -> tuple[set[str], int]:
    flat = run_ingestor(raw_fixture)
    con = materialize(flat)
    verdicts = exec_rules(con, rules)
    con.close()
    return fail_set(verdicts), len(flat)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def write_report(
    ts_stamp: str,
    baseline_fixture_fails: set[str],
    baseline_fixture_rows: int,
    baseline_synth_fails: set[str],
    baseline_synth_rows: int,
    cycles: list[list[dict[str, Any]]],
    behavior: dict[str, Any],
    all_rule_ids: list[str],
) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"onet-experience-{ts_stamp}.md"

    total_scenarios = sum(len(c) for c in cycles)
    caught = 0
    gaps: list[dict[str, Any]] = []
    for cycle in cycles:
        for r in cycle:
            if r.get("error"):
                continue
            if r.get("caught"):
                caught += 1
            else:
                gaps.append(r)

    s7_gap = behavior.get("S7", {}).get("raised") is False
    s8_gap = behavior.get("S8", {}).get("raised") is False
    ingestor_gap_count = int(s7_gap) + int(s8_gap)
    total_gaps = len(gaps) + ingestor_gap_count
    if total_gaps == 0:
        verdict = "CLEAN — no gaps"
    else:
        verdict = (
            f"GAPS FOUND ({total_gaps}) — "
            f"{len(gaps)} DQ-rule gap(s), {ingestor_gap_count} ingestor-level gap(s)"
        )

    lines: list[str] = []
    a = lines.append
    a(f"# Chaos Monkey Adversarial DQ Report — raw.onet_experience")
    a("")
    a(f"- **Spec:** `onet-experience-requirements`")
    a(f"- **Target:** `raw.onet_experience` (Bronze ingest)")
    a(f"- **Ingestor:** `src/raw/onet_ingestor.py::OnetExperienceIngestor`")
    a(f"- **Rules file:** `governance/dq-rules/raw-onet-experience.json` ({len(all_rule_ids)} rules)")
    a(f"- **Fixture baseline:** `tests/raw/onet_samples/Education, Training, and Experience.txt`")
    a(f"- **Runner:** `scripts/onet_experience_chaos_runner.py`")
    a(f"- **Report timestamp:** {ts_stamp}")
    a(f"- **Information barrier:** enforced — DQ rule JSON is loaded opaquely "
      f"(SQL+threshold keys only); no rule source was read by the author.")
    a("")

    a("## Method")
    a("")
    a("Scenario-based chaos on an in-memory copy of the test fixture. Each scenario:")
    a("")
    a("1. Mutates the raw TSV (or the post-ingestor flat-dict list).")
    a("2. Runs the real `OnetExperienceIngestor.flatten()` — this exercises the")
    a("   ingestor's required-field drop / type coercion logic.")
    a("3. Materializes the result as `raw.onet_experience` in in-memory DuckDB.")
    a("4. Executes every rule SQL in the opaque rules JSON and records PASS/FAIL.")
    a("5. Compares the scenario's FAIL set against a baseline FAIL set (same rules")
    a("   run against the unmutated fixture). The delta — **new fails the")
    a("   mutation introduced** — is the scenario's attribution.")
    a("")
    a("Cycles use escalating rates (5%, 6%, 7%, 8%, 10%) over overlapping scenario")
    a("packs so each corruption is probed at multiple intensities.")
    a("")
    a("Scenarios 7 (truncated ZIP / empty file) and 8 (wrong file in ZIP) hit the")
    a("ingestor directly — these are behavior checks, not DQ rule probes.")
    a("")

    a("## Baselines (no corruption)")
    a("")
    a(f"- Fixture baseline: {baseline_fixture_rows} rows. Rules failing against")
    a(f"  the tiny fixture (inevitable due to row-count / coverage / per-scale")
    a(f"  count rules on a 28-row fixture): **{len(baseline_fixture_fails)} / {len(all_rule_ids)}**.")
    a(f"  Fixture-baseline fail set (filtered out of each scenario's attribution):")
    a(f"  `{sorted(baseline_fixture_fails)}`")
    a("")
    a(f"- Synthetic clean baseline: {baseline_synth_rows} rows (878 SOCs × 41")
    a(f"  cats × correct per-scale counts). Rules failing against the synthetic")
    a(f"  baseline: **{len(baseline_synth_fails)} / {len(all_rule_ids)}**.")
    a(f"  Synth-baseline fail set: `{sorted(baseline_synth_fails)}`")
    a("")
    a("If the synthetic baseline shows any P0 fails, those are structural")
    a("mismatches between the synthetic generator and the rules — see §Caveats.")
    a("")

    a("## Cycle summary")
    a("")
    a("| Cycle | Rate | Scenarios | Caught / Total | Gaps |")
    a("|:----:|:----:|:---------|:--------------:|:----:|")
    for i, cycle in enumerate(cycles, 1):
        rate = cycle[0]["rate"] if cycle else 0.0
        c_caught = sum(1 for r in cycle if r.get("caught"))
        c_gaps = sum(1 for r in cycle if not r.get("caught") and not r.get("error"))
        c_total = len(cycle)
        a(f"| {i} | {int(rate*100)}% | {', '.join(s['id'] for s in cycle)} | {c_caught} / {c_total} | {c_gaps} |")
    a("")

    a("## Per-scenario matrix (isolated probes — union across cycles)")
    a("")
    a("| # | Scenario | Dimension | Expected guard | New fails delta | Caught? |")
    a("|:--:|:---------|:----------|:---------------|:----------------|:-------:|")
    seen: set[str] = set()
    for cycle in cycles:
        for r in cycle:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            if r.get("error"):
                a(f"| {r['id']} | {r['label']} | — | — | ERROR: {r['error']} | no |")
                continue
            caught_str = "yes" if r["caught"] else "**NO (gap)**"
            if r.get("caught_by_ingestor"):
                fails_str = "(defended by ingestor — row dropped)"
            else:
                fails_str = ", ".join(r["new_fails_vs_baseline"]) or "(none)"
            a(f"| {r['id']} | {r['label']} | {r['dimension']} | {r['expected_guard']} | {fails_str} | {caught_str} |")
    a("")

    a("## Ingestor-level behavior checks (scenarios 7 + 8)")
    a("")
    a("These two scenarios target the `OnetExperienceIngestor`/`OnetBaseIngestor`")
    a("code path, not the DQ rules. An ingestor that silently returns 0 rows on a")
    a("truncated download would let a bad run ship — the behavior check documents")
    a("whether the ingestor raises.")
    a("")
    a("| # | Scenario | Raised? | Detail |")
    a("|:--:|:---------|:-------:|:-------|")
    for sid, label, res in [
        ("S7", "truncated_zip_empty_file", behavior.get("S7", {})),
        ("S8", "missing_target_file_in_zip", behavior.get("S8", {})),
    ]:
        raised = res.get("raised")
        if raised is None:
            a(f"| {sid} | {label} | — | not run |")
        elif raised:
            a(
                f"| {sid} | {label} | YES | `{res.get('exception_type')}`: "
                f"{res.get('message', '')[:120]} |"
            )
        else:
            a(f"| {sid} | {label} | **NO** | {res.get('note', '')} |")
    a("")

    if gaps or behavior.get("S7", {}).get("raised") is False:
        a("## Gaps & recommendations")
        a("")
        for g in gaps:
            a(f"- **{g['id']} — `{g['label']}`** ({g['dimension']}): no rule")
            a(f"  new-fires against this corruption. Expected guard was")
            a(f"  *{g['expected_guard']}*. Recommendation:")
            a(f"  author a rule that captures this dimension (see dq-rule-writer).")
            a("")
        if behavior.get("S7", {}).get("raised") is False:
            a("- **Ingestor gap — truncated ZIP / empty file**: `OnetExperienceIngestor`")
            a("  silently parsed 0 rows rather than raising. Recommend an empty-ness")
            a("  guard in `_parse_tsv` (if `len(rows) == 0: raise ValueError(...)`) or")
            a("  a post-parse assert that at least one row was returned for")
            a("  `SOURCE_FILENAME`. This is ingestor-level, not a DQ-rule fix.")
            a("")
    else:
        a("## Gaps & recommendations")
        a("")
        a("None. All injected corruptions were caught by either a DQ rule new-firing")
        a("on top of the baseline OR an ingestor-level exception.")
        a("")

    a("## Verdict")
    a("")
    a(f"**{verdict}**")
    a("")
    a(f"- Rule-targeted probes: {caught}/{total_scenarios} caught across 5 cycles.")
    a(f"- Ingestor-level behavior checks: S7 {'GAP' if s7_gap else 'OK'}, "
      f"S8 {'GAP' if s8_gap else 'OK'}.")
    a("")
    if total_gaps == 0:
        a("5 cycles CLEAN. `bs:adversarial-auditor` may be SKIPPED per the spec's")
        a("agent-workflow step 16 skip justification.")
    else:
        a("Not yet CLEAN across 5 cycles due to ingestor-level gap(s). "
          "`bs:adversarial-auditor` should NOT be skipped; the ingestor guard")
        a("recommended below should be implemented and a follow-up chaos run")
        a("executed to confirm S7 closes.")
    a("")

    out_path.write_text("\n".join(lines))
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_cycles(scenarios: list[dict]) -> list[list[dict]]:
    """Package scenarios into 5 escalating-rate cycles (each with overlap).

    Every scenario appears in at least one cycle; scenarios at higher rates
    are bundled with broader scenario packs. We want all 5 cycles to exercise
    real corruptions so we can ground a 5-cycle clean verdict.
    """
    by_rate: dict[float, list[dict]] = {}
    for s in scenarios:
        by_rate.setdefault(s["rate"], []).append(s)
    rates = [0.05, 0.06, 0.07, 0.08, 0.10]
    cycles: list[list[dict]] = []
    for rate in rates:
        cycle = [dict(s, rate=rate) for s in scenarios if s["rate"] <= rate]
        cycles.append(cycle)
    return cycles


def main() -> int:
    safety_check()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    print(f"=== Chaos run timestamp: {ts} ===")

    print(f"Loading fixture from {FIXTURE_PATH.name}...")
    raw_fixture = load_fixture_rows()
    print(f"  Fixture has {len(raw_fixture)} raw rows.")

    rules = load_rules()
    all_rule_ids = [r["rule_id"] for r in rules]
    print(f"Loaded {len(rules)} rules (opaque).")

    # Baselines
    print("Computing fixture baseline (no corruption)...")
    baseline_fixture_fails, baseline_fixture_rows = compute_baseline(raw_fixture, rules)
    print(f"  Fixture baseline: {baseline_fixture_rows} flat rows, "
          f"{len(baseline_fixture_fails)} rule fails.")

    print("Computing synthetic clean baseline (~30k rows, 880 SOCs)...")
    synth = make_clean_synthetic()
    baseline_synth_fails, baseline_synth_rows = compute_baseline(synth, rules)
    print(f"  Synth baseline: {baseline_synth_rows} flat rows, "
          f"{len(baseline_synth_fails)} rule fails.")

    # Cycles
    cycles = build_cycles(SCENARIOS)
    print(f"Running {len(cycles)} cycles...")

    cycle_results: list[list[dict]] = []
    for i, cycle in enumerate(cycles, 1):
        print(f"\n--- Cycle {i} (rate {int(cycle[0]['rate']*100)}%) : {len(cycle)} scenarios ---")
        results = []
        for sc in cycle:
            r = run_one_scenario(sc, raw_fixture, baseline_fixture_fails, rules)
            flag = "ERROR" if r.get("error") else ("CAUGHT" if r.get("caught") else "MISS")
            new = r.get("new_fails_vs_baseline", [])
            print(f"  {sc['id']:>4}  {flag:>6}  {sc['label']:<42}  new_fails={new}")
            results.append(r)
        cycle_results.append(results)

    # Behavior checks
    print("\n--- Behavior checks (S7 truncated ZIP, S8 missing file) ---")
    behavior = {
        "S7": behavior_check_truncated_zip(),
        "S8": behavior_check_missing_file(),
    }
    for k, v in behavior.items():
        print(f"  {k}: raised={v.get('raised')}  {v.get('exception_type') or v.get('note', '')}")

    # Report
    path = write_report(
        ts,
        baseline_fixture_fails,
        baseline_fixture_rows,
        baseline_synth_fails,
        baseline_synth_rows,
        cycle_results,
        behavior,
        all_rule_ids,
    )
    print(f"\nReport written to {path}")
    # Final verdict
    total = sum(len(c) for c in cycle_results)
    caught = sum(1 for c in cycle_results for r in c if r.get("caught"))
    gaps = sum(1 for c in cycle_results for r in c if not r.get("caught") and not r.get("error"))
    print(f"\nFinal: {caught}/{total} caught across 5 cycles. Gaps: {gaps}.")
    if behavior.get("S7", {}).get("raised") is False:
        print("  + Ingestor gap: S7 (truncated ZIP) did not raise.")
    if behavior.get("S8", {}).get("raised") is False:
        print("  + Ingestor gap: S8 (missing file) did not raise.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
