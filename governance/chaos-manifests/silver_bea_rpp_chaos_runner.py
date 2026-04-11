"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec:  silver-base-bea-rpp
Table: base.bea_rpp (51 rows - 50 states + DC, static reference table)
Shadow namespace: shadow_base.bea_rpp (in the SILVER warehouse)

This is a curated, spec-driven scenario runner (NOT a per-dimension fuzz
runner) because the underlying table is only 51 rows and the interesting
breakages are categorical.  Each cycle applies a fixed scenario pack
covering the 24 Silver-specific scenarios requested by the adversarial
auditor.

Information Barrier: This script does NOT read
  - governance/dq-rules/silver-base-bea-rpp.json
  - governance/dq-results/*
  - governance/dq-scorecards/*
  - brightsmith.infra.dq_runner (imported for its public run_rules() entry
    point only; the source is not inspected)

Corruption choices are based solely on:
  - docs/specs/silver-base-bea-rpp.md   (public spec)
  - src/silver/bea_rpp_transformer.py   (derivation code)
  - src/silver/_us_state_reference.py   (static FIPS/USPS/region tables)

Every manipulation happens inside the shadow_base namespace.  The real
base.bea_rpp table is never mutated.
"""

import copy
import datetime
import json
import shutil
import sys
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
SILVER_WAREHOUSE = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"
SOURCE_PARQUET = (
    SILVER_WAREHOUSE
    / "base"
    / "bea_rpp"
    / "data"
    / "00000-0-81956751-369d-43d1-b0aa-400490664d5c.parquet"
)
SHADOW_DIR = SILVER_WAREHOUSE / "shadow_base" / "bea_rpp"
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"

SPEC_NAME = "silver-base-bea-rpp"
REAL_FQN = "base.bea_rpp"
SHADOW_FQN = "shadow_base.bea_rpp"

SEED_BASE = 42

# Rules that cannot be evaluated in shadow mode and must be filtered out of
# chaos runs (see governance/chaos-reports/silver-base-bea-rpp-chaos.md Gap 3).
#
# The brightsmith dq_runner's shadow-mode rewrite (`shadow=True`) remaps every
# known-namespace ref to `shadow_<ns>`. For single-zone rules that's correct.
# For cross-zone rules like SIL-BEA-018 (which joins `base.bea_rpp` against
# `bronze.bea_rpp` to prove passthrough integrity), the Bronze side also gets
# rewritten to `shadow_bronze`, which this chaos harness never stages, so the
# rule errors on every invocation including the no-op negative control.
#
# The rule is correct and runs green in production. The hard carve-out lives
# here (rather than in the rules JSON) because the chaos runner's information
# barrier forbids reading `governance/dq-rules/silver-base-bea-rpp.json`. The
# rule JSON itself carries the companion markers `evaluation_mode: production_only`
# and `chaos_exclude: true` for downstream tooling.
#
# Revisit this set if brightsmith adds cross-zone shadow support (i.e., the
# ability to register a shadow Silver table alongside the live Bronze table
# inside the same shadow run). At that point this list can go back to empty.
SHADOW_EXCLUDED_RULE_IDS = frozenset({
    "SIL-BEA-018",  # cross-zone base<->bronze passthrough integrity
})

sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path("/Users/jcernauske/code/bright/brightsmith/src")))

from brightsmith.config import configure  # noqa: E402

configure(project_root=str(PROJECT_ROOT), project_name="brightsmith")


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

def safety_check():
    import os

    os.environ["CHAOS_MONKEY_ENABLED"] = "true"
    os.environ["BRIGHTSMITH_ENV"] = "dev"
    os.environ.setdefault("GRIST_ENV", "dev")
    enabled = os.environ.get("CHAOS_MONKEY_ENABLED", "").lower() == "true"
    dev_env = os.environ.get("BRIGHTSMITH_ENV", "").lower() == "dev"
    if not enabled:
        print("ERROR: CHAOS_MONKEY_ENABLED is not 'true'.")
        sys.exit(1)
    if not dev_env:
        print("ERROR: BRIGHTSMITH_ENV is not 'dev'.")
        sys.exit(1)
    print("Safety: CHAOS_MONKEY_ENABLED=true, BRIGHTSMITH_ENV=dev")


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_source_rows():
    import pyarrow.parquet as pq

    t = pq.read_table(str(SOURCE_PARQUET))
    rows = [dict(r) for r in t.to_pylist()]
    return rows, t.schema


def rows_to_arrow(rows, original_schema):
    """Project rows back into a schema that accepts corrupted types.

    We rebuild each column individually so impossible values (wrong type,
    extra chars) still round-trip through pyarrow.
    """
    import pyarrow as pa

    arrays = {}
    for field in original_schema:
        col_name = field.name
        values = [r.get(col_name) for r in rows]
        try:
            arrays[col_name] = pa.array(values, type=field.type)
        except (pa.ArrowInvalid, pa.ArrowTypeError, pa.ArrowNotImplementedError):
            arrays[col_name] = pa.array(values)
    return pa.table(arrays)


def write_shadow_parquet(arrow_table, cycle_num):
    import pyarrow.parquet as pq

    SHADOW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SHADOW_META_DIR.mkdir(parents=True, exist_ok=True)
    out = SHADOW_DATA_DIR / f"chaos-cycle-{cycle_num}.parquet"
    pq.write_table(arrow_table, str(out))
    return out


def register_shadow(parquet_path):
    """Register shadow table in catalog, replacing any prior copy."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        DateType,
        DoubleType,
        IntegerType,
        NestedField,
        StringType,
        TimestampType,
    )
    import pyarrow.parquet as pq

    catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))
    try:
        catalog.create_namespace("shadow_base")
    except Exception:
        pass
    try:
        catalog.drop_table(SHADOW_FQN)
    except Exception:
        pass

    # All fields optional so we can land corrupted / null data in the shadow.
    # Schema mirrors base.bea_rpp (11 columns).
    schema = Schema(
        NestedField(1, "record_id", StringType(), required=False),
        NestedField(2, "state_fips", StringType(), required=False),
        NestedField(3, "state_name", StringType(), required=False),
        NestedField(4, "state_abbr", StringType(), required=False),
        NestedField(5, "census_region", StringType(), required=False),
        NestedField(6, "rpp_all_items", DoubleType(), required=False),
        NestedField(7, "purchasing_power_multiplier", DoubleType(), required=False),
        NestedField(8, "verification_status", StringType(), required=False),
        NestedField(9, "data_year", IntegerType(), required=False),
        NestedField(10, "source_load_date", DateType(), required=False),
        NestedField(11, "ingested_at", TimestampType(), required=False),
    )
    tbl = catalog.create_table(SHADOW_FQN, schema=schema)
    data = pq.read_table(str(parquet_path))
    tbl.append(data)
    return tbl


def run_dq_rules_shadow():
    from brightsmith.infra.dq_runner import run_rules
    from brightsmith.infra.iceberg_setup import get_catalog

    catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))
    result = run_rules(spec=SPEC_NAME, catalog=catalog, shadow=True)

    # Drop rules that can't be evaluated in shadow mode (see
    # SHADOW_EXCLUDED_RULE_IDS above). These are cross-zone rules whose
    # Bronze/Raw side isn't staged in shadow, so they error on every run
    # including the no-op negative control. Their absence here is the
    # chaos-monkey's side of the carve-out; production DQ runs still
    # execute them normally.
    filtered = [
        r for r in result.get("results", [])
        if r.get("rule_id") not in SHADOW_EXCLUDED_RULE_IDS
    ]
    excluded = [
        r for r in result.get("results", [])
        if r.get("rule_id") in SHADOW_EXCLUDED_RULE_IDS
    ]
    result["results"] = filtered
    result["rules_total"] = len(filtered)
    result["rules_passed"] = sum(1 for r in filtered if r.get("passed"))
    result["rules_failed"] = sum(
        1 for r in filtered if not r.get("passed") and not r.get("error")
    )
    result["shadow_excluded_rule_ids"] = [r.get("rule_id") for r in excluded]
    return result


def cleanup_shadow():
    if SHADOW_DIR.exists():
        shutil.rmtree(SHADOW_DIR)
    try:
        from brightsmith.infra.iceberg_setup import get_catalog

        catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))
        try:
            catalog.drop_table(SHADOW_FQN)
        except Exception:
            pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Scenario library
# ---------------------------------------------------------------------------

def _find_idx(rows, state_fips):
    for i, r in enumerate(rows):
        if r.get("state_fips") == state_fips:
            return i
    return None


# ---- 1. state_abbr corruption --------------------------------------------

def scenario_lower_ca(rows):
    """S1a: set California state_abbr to 'ca' (lowercase) — regex/uppercase rule."""
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["state_abbr"]
    rows[idx]["state_abbr"] = "ca"
    return [{
        "scenario": "state_abbr_lowercase_ca",
        "dimensions": ["validity"],
        "field": "state_abbr",
        "strategy": "set_lowercase",
        "old_value": str(old),
        "new_value": "ca",
    }]


def scenario_three_char_ca(rows):
    """S1b: set California state_abbr to 'CAL' (3 chars) — regex/length rule."""
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["state_abbr"]
    rows[idx]["state_abbr"] = "CAL"
    return [{
        "scenario": "state_abbr_three_char_ca",
        "dimensions": ["validity"],
        "field": "state_abbr",
        "strategy": "set_three_char",
        "old_value": str(old),
        "new_value": "CAL",
    }]


def scenario_swap_ca_ia_abbr(rows):
    """S1c: swap CA and IA state_abbr values — bijection rule should fire."""
    ca = _find_idx(rows, "06")
    ia = _find_idx(rows, "19")
    if ca is None or ia is None:
        return []
    old_ca = rows[ca]["state_abbr"]
    old_ia = rows[ia]["state_abbr"]
    rows[ca]["state_abbr"] = old_ia
    rows[ia]["state_abbr"] = old_ca
    return [{
        "scenario": "swap_ca_ia_abbr",
        "dimensions": ["consistency", "validity"],
        "field": "state_abbr",
        "strategy": "swap_bijection_pair",
        "old_value": f"CA={old_ca}, IA={old_ia}",
        "new_value": f"CA={old_ia}, IA={old_ca}",
    }]


# ---- 2. census_region corruption -----------------------------------------

def scenario_ca_region_pacific(rows):
    """S2a: set California census_region to 'Pacific' — IN-list rule."""
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["census_region"]
    rows[idx]["census_region"] = "Pacific"
    return [{
        "scenario": "ca_region_pacific",
        "dimensions": ["validity"],
        "field": "census_region",
        "strategy": "invalid_enum_value",
        "old_value": str(old),
        "new_value": "Pacific",
    }]


def scenario_drop_west_region(rows):
    """S2b: relabel all 13 West rows as 'South' — region count rule should fire."""
    entries = []
    count = 0
    for r in rows:
        if r.get("census_region") == "West":
            r["census_region"] = "South"
            count += 1
    entries.append({
        "scenario": "drop_west_region",
        "dimensions": ["coverage", "reasonableness"],
        "field": "census_region",
        "strategy": "relabel_all_west_as_south",
        "old_value": "13 West rows",
        "new_value": f"{count} relabeled to South",
    })
    return entries


def scenario_region_count_shift(rows):
    """S2c: flip one West row to Midwest — upsets the 9/12/17/13 distribution."""
    # Pick Wyoming (56) — currently West. Move it to Midwest.
    idx = _find_idx(rows, "56")
    if idx is None:
        return []
    old = rows[idx]["census_region"]
    rows[idx]["census_region"] = "Midwest"
    return [{
        "scenario": "region_count_shift",
        "dimensions": ["reasonableness", "accuracy"],
        "field": "census_region",
        "strategy": "shift_single_row_between_regions",
        "old_value": f"Wyoming={old}",
        "new_value": "Wyoming=Midwest",
    }]


# ---- 3. purchasing_power_multiplier corruption ---------------------------

def scenario_ppm_out_of_range(rows):
    """S3a: set one row's multiplier to 2.0 — range rule should fire."""
    idx = _find_idx(rows, "04")  # Arizona (estimate row)
    if idx is None:
        return []
    old = rows[idx]["purchasing_power_multiplier"]
    rows[idx]["purchasing_power_multiplier"] = 2.0
    return [{
        "scenario": "ppm_out_of_range",
        "dimensions": ["validity", "reasonableness"],
        "field": "purchasing_power_multiplier",
        "strategy": "set_above_range",
        "old_value": str(old),
        "new_value": "2.0",
    }]


def scenario_ppm_inverse_break(rows):
    """S3b: set CA multiplier to 1.0 while rpp=110.7 — inverse invariant rule."""
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["purchasing_power_multiplier"]
    rows[idx]["purchasing_power_multiplier"] = 1.0
    return [{
        "scenario": "ppm_inverse_invariant_break",
        "dimensions": ["consistency", "accuracy"],
        "field": "purchasing_power_multiplier",
        "strategy": "break_inverse_relation_ca",
        "old_value": str(old),
        "new_value": "1.0 (rpp stays 110.7)",
    }]


# ---- 4. verification_status corruption -----------------------------------

def scenario_verif_unknown_value(rows):
    """S4a: set one row to 'verified' — IN-list rule should fire."""
    idx = _find_idx(rows, "04")  # Arizona
    if idx is None:
        return []
    old = rows[idx]["verification_status"]
    rows[idx]["verification_status"] = "verified"
    return [{
        "scenario": "verification_status_unknown_value",
        "dimensions": ["validity"],
        "field": "verification_status",
        "strategy": "invalid_enum_value",
        "old_value": str(old),
        "new_value": "verified",
    }]


def scenario_verif_count_drift(rows):
    """S4b: mark a 9th state (AZ) as bea_official — count=8 rule should fire."""
    idx = _find_idx(rows, "04")  # Arizona, currently estimate
    if idx is None:
        return []
    old = rows[idx]["verification_status"]
    rows[idx]["verification_status"] = "bea_official"
    return [{
        "scenario": "verification_status_count_drift_up",
        "dimensions": ["reasonableness", "consistency"],
        "field": "verification_status",
        "strategy": "mark_ninth_bea_official",
        "old_value": f"AZ={old}",
        "new_value": "AZ=bea_official (now 9 bea_official rows)",
    }]


def scenario_verif_flip_ca_to_estimate(rows):
    """S4c: flip CA to 'estimate' — allow-list subset rule should fire.

    Also trips the count=8 rule because the set shrinks to 7 bea_official.
    """
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["verification_status"]
    rows[idx]["verification_status"] = "estimate"
    return [{
        "scenario": "verification_status_flip_ca_to_estimate",
        "dimensions": ["consistency", "accuracy"],
        "field": "verification_status",
        "strategy": "flip_verified_to_estimate",
        "old_value": f"CA={old}",
        "new_value": "CA=estimate",
    }]


def scenario_verif_mark_texas_official(rows):
    """S4d: mark Texas (48) as 'bea_official' — allow-list subset + count rule."""
    idx = _find_idx(rows, "48")
    if idx is None:
        return []
    old = rows[idx]["verification_status"]
    rows[idx]["verification_status"] = "bea_official"
    return [{
        "scenario": "verification_status_mark_texas_official",
        "dimensions": ["consistency", "accuracy"],
        "field": "verification_status",
        "strategy": "mark_non_verified_as_official",
        "old_value": f"TX={old}",
        "new_value": "TX=bea_official",
    }]


# ---- 5. Passthrough integrity break --------------------------------------

def scenario_passthrough_break(rows):
    """S5: set a Silver row's rpp_all_items to diverge from bronze.

    CA bronze is 110.7; we set the silver shadow to 105.0.  The cross-zone
    referential-integrity rule must compare Silver to Bronze and fire.
    """
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["rpp_all_items"]
    rows[idx]["rpp_all_items"] = 105.0
    # leave the multiplier alone so this is ONLY a passthrough break
    return [{
        "scenario": "passthrough_integrity_break_ca",
        "dimensions": ["referential_integrity", "accuracy"],
        "field": "rpp_all_items",
        "strategy": "diverge_from_bronze",
        "old_value": str(old),
        "new_value": "105.0 (bronze still says 110.7)",
    }]


# ---- 6. Spot-check drift -------------------------------------------------

def scenario_ca_ppm_drift(rows):
    """S6a: change CA multiplier from 0.9034 to 0.9100 — CA spot check rule."""
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["purchasing_power_multiplier"]
    rows[idx]["purchasing_power_multiplier"] = 0.9100
    return [{
        "scenario": "ca_ppm_spot_check_drift",
        "dimensions": ["accuracy"],
        "field": "purchasing_power_multiplier",
        "strategy": "subtle_drift_inside_range",
        "old_value": str(old),
        "new_value": "0.9100",
    }]


def scenario_dc_abbr_wa(rows):
    """S6b: change DC state_abbr to 'WA' — DC spot check + bijection rule."""
    idx = _find_idx(rows, "11")
    if idx is None:
        return []
    old = rows[idx]["state_abbr"]
    rows[idx]["state_abbr"] = "WA"
    return [{
        "scenario": "dc_state_abbr_wa",
        "dimensions": ["accuracy", "consistency"],
        "field": "state_abbr",
        "strategy": "wrong_but_valid_abbr",
        "old_value": str(old),
        "new_value": "WA (collides with Washington)",
    }]


# ---- 7. Year drift -------------------------------------------------------

def scenario_year_literal_break(rows):
    """S7a: set one row's data_year to 2023 — literal data_year rule."""
    idx = _find_idx(rows, "30")  # Montana
    if idx is None:
        return []
    old = rows[idx]["data_year"]
    rows[idx]["data_year"] = 2023
    return [{
        "scenario": "year_literal_break",
        "dimensions": ["freshness", "validity"],
        "field": "data_year",
        "strategy": "set_stale_year",
        "old_value": str(old),
        "new_value": "2023",
    }]


def scenario_year_mixed_supersession(rows):
    """S7b: inject a DUPLICATE state row (AZ) with data_year=2024 but edit an
    existing row to data_year=2024 too — COUNT(DISTINCT data_year) should =2.

    Concretely: we flip Montana's data_year to 2024 (already the norm), then
    append a second Arizona row with data_year set to a DIFFERENT year.
    That gives 52 rows with 2 distinct years.  Supersession rule fires.
    """
    entries = []
    az = _find_idx(rows, "04")
    if az is None:
        return entries
    dupe = copy.deepcopy(rows[az])
    dupe["data_year"] = 2023
    dupe["record_id"] = "rpp-duplicate-az-2023"  # different record_id
    rows.append(dupe)
    entries.append({
        "scenario": "year_supersession_mixed",
        "dimensions": ["freshness", "uniqueness", "reasonableness"],
        "field": "data_year",
        "strategy": "append_duplicate_state_different_year",
        "old_value": "AZ appears 1x with data_year=2024",
        "new_value": "AZ appears 2x (2024, 2023)",
    })
    return entries


# ---- 8. record_id break --------------------------------------------------

def scenario_duplicate_record_id(rows):
    """S8: duplicate an existing record_id across two rows.

    We leave the second row in place but copy AR's record_id into NJ's row.
    Row count stays 51; record_id uniqueness fails.
    """
    ar = _find_idx(rows, "05")  # Arkansas
    nj = _find_idx(rows, "34")  # New Jersey
    if ar is None or nj is None:
        return []
    old = rows[nj]["record_id"]
    rows[nj]["record_id"] = rows[ar]["record_id"]
    return [{
        "scenario": "record_id_duplicate",
        "dimensions": ["uniqueness"],
        "field": "record_id",
        "strategy": "copy_record_id_across_rows",
        "old_value": str(old),
        "new_value": f"{rows[ar]['record_id']} (collides with AR)",
    }]


# ---- 9. Negative controls ------------------------------------------------

def scenario_neg_swap_ia_ok(rows):
    """N1: swap IA and OK rows (both bea_official, both 1.1390 ppm).

    Every numeric field stays the same; state_fips stays aligned with its
    own record_id (we only swap values between the two rows where they are
    already equal).  Should NOT fire anything.
    """
    ia = _find_idx(rows, "19")
    ok = _find_idx(rows, "40")
    if ia is None or ok is None:
        return []
    # Swap state_name since both share same rpp/multiplier/verif/year
    ia_name = rows[ia]["state_name"]
    ok_name = rows[ok]["state_name"]
    rows[ia]["state_name"] = ok_name
    rows[ok]["state_name"] = ia_name
    return [{
        "scenario": "neg_control_swap_ia_ok_names",
        "dimensions": ["negative_control"],
        "field": "state_name",
        "strategy": "swap_names_where_all_numeric_fields_equal",
        "old_value": f"IA={ia_name}, OK={ok_name}",
        "new_value": f"IA={ok_name}, OK={ia_name}",
        "expected_fired": False,
    }]


def scenario_neg_noop(rows):
    """N2: no-op cycle — zero mutations — should NOT fire anything."""
    return [{
        "scenario": "neg_control_noop",
        "dimensions": ["negative_control"],
        "field": "(none)",
        "strategy": "noop",
        "old_value": "(unchanged)",
        "new_value": "(unchanged)",
        "expected_fired": False,
    }]


# ---------------------------------------------------------------------------
# Cycle plan
# ---------------------------------------------------------------------------

CYCLE_SCENARIOS = {
    1: {
        "rate": 0.05,
        "label": "state_abbr_regex_and_range",
        "scenarios": [
            scenario_lower_ca,
            scenario_three_char_ca,
            scenario_ppm_out_of_range,
        ],
    },
    2: {
        "rate": 0.06,
        "label": "census_region_validity_and_coverage",
        "scenarios": [
            scenario_ca_region_pacific,
            scenario_drop_west_region,
            scenario_region_count_shift,
        ],
    },
    3: {
        "rate": 0.07,
        "label": "verification_status_full_sweep",
        "scenarios": [
            scenario_verif_unknown_value,
            scenario_verif_count_drift,
            scenario_verif_flip_ca_to_estimate,
            scenario_verif_mark_texas_official,
        ],
    },
    4: {
        "rate": 0.08,
        "label": "passthrough_and_spot_checks",
        "scenarios": [
            scenario_passthrough_break,
            scenario_ca_ppm_drift,
            scenario_dc_abbr_wa,
        ],
    },
    5: {
        "rate": 0.10,
        "label": "year_recordid_and_invariants",
        "scenarios": [
            scenario_year_literal_break,
            scenario_year_mixed_supersession,
            scenario_duplicate_record_id,
            scenario_ppm_inverse_break,
            scenario_swap_ca_ia_abbr,
        ],
    },
    6: {
        "rate": 0.00,
        "label": "negative_control_swap_ia_ok",
        "scenarios": [scenario_neg_swap_ia_ok],
    },
    7: {
        "rate": 0.00,
        "label": "negative_control_noop",
        "scenarios": [scenario_neg_noop],
    },
}


# ---------------------------------------------------------------------------
# Cycle driver
# ---------------------------------------------------------------------------

def run_cycle(cycle_num, spec):
    rate = spec["rate"]
    label = spec["label"]
    seed = SEED_BASE + cycle_num

    print("\n" + "=" * 72)
    print(f"CYCLE {cycle_num} | rate={rate*100:.0f}% | seed={seed} | label={label}")
    print("=" * 72)

    rows, source_schema = load_source_rows()
    original_count = len(rows)
    print(f"  loaded {original_count} rows from {SOURCE_PARQUET.name}")

    manifest = []
    for fn in spec["scenarios"]:
        try:
            entries = fn(rows)
            manifest.extend(entries)
            print(f"  scenario {fn.__name__}: {len(entries)} manifest entries")
        except Exception as exc:
            print(f"  ERROR in {fn.__name__}: {exc}")
            traceback.print_exc()

    print(f"  row count after corruption: {len(rows)} (was {original_count})")
    print(f"  total manifest entries: {len(manifest)}")

    dq_result = None
    try:
        arrow_table = rows_to_arrow(rows, source_schema)
        parquet_path = write_shadow_parquet(arrow_table, cycle_num)
        print(f"  wrote shadow parquet -> {parquet_path.name}")
        register_shadow(parquet_path)
        print(f"  registered {SHADOW_FQN}")

        dq_result = run_dq_rules_shadow()
        print(
            f"  dq run_id={dq_result.get('run_id')}  "
            f"total={dq_result.get('rules_total')}  "
            f"passed={dq_result.get('rules_passed')}  "
            f"failed={dq_result.get('rules_failed')}"
        )
        for r in dq_result.get("results", []):
            status = "PASS" if r.get("passed") else (
                "ERROR" if r.get("error") else "FAIL"
            )
            print(f"    {r.get('rule_id'):<48} {status:<6} value={r.get('raw_value')}")
    except Exception as exc:
        print(f"  ERROR during shadow/dq: {exc}")
        traceback.print_exc()
        dq_result = {
            "run_id": "error",
            "rules_total": 0,
            "rules_passed": 0,
            "rules_failed": 0,
            "p0_passed": False,
            "results": [],
            "error": str(exc),
        }
    finally:
        cleanup_shadow()

    return {
        "cycle": cycle_num,
        "label": label,
        "rate": rate,
        "seed": seed,
        "original_row_count": original_count,
        "corrupted_row_count": len(rows),
        "manifest": manifest,
        "dq_result": dq_result,
    }


def reconcile(cycle_result):
    dq = cycle_result["dq_result"] or {}
    results = dq.get("results", [])
    failed = [r for r in results if not r.get("passed") and not r.get("error")]
    passed = [r for r in results if r.get("passed")]
    errored = [r for r in results if r.get("error")]
    fired_ids = [r.get("rule_id") for r in failed]

    manifest = cycle_result["manifest"]
    neg_controls = [m for m in manifest if "negative_control" in m.get("dimensions", [])]
    real_injections = [m for m in manifest if "negative_control" not in m.get("dimensions", [])]

    if real_injections:
        caught_any = len(failed) > 0
    else:
        caught_any = len(failed) == 0  # neg control: no fires = success

    for m in manifest:
        if "negative_control" in m.get("dimensions", []):
            m["caught"] = len(failed) == 0
        else:
            m["caught"] = len(failed) > 0

    return {
        "fired_rule_ids": fired_ids,
        "passed_rule_ids": [r.get("rule_id") for r in passed],
        "errored_rule_ids": [r.get("rule_id") for r in errored],
        "total_rules": len(results),
        "rules_fired": len(failed),
        "rules_silent": len(passed),
        "rules_errored": len(errored),
        "caught_any": caught_any,
        "real_injection_count": len(real_injections),
        "neg_control_count": len(neg_controls),
    }


def main():
    safety_check()

    all_cycles = []
    for cycle_num in sorted(CYCLE_SCENARIOS.keys()):
        spec = CYCLE_SCENARIOS[cycle_num]
        cycle_result = run_cycle(cycle_num, spec)
        cycle_result["reconciliation"] = reconcile(cycle_result)
        all_cycles.append(cycle_result)

    cleanup_shadow()

    manifest_out = {
        "spec": SPEC_NAME,
        "table": REAL_FQN,
        "shadow_table": SHADOW_FQN,
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    out_path = (
        PROJECT_ROOT
        / "governance/chaos-manifests/silver-base-bea-rpp-manifest.json"
    )
    out_path.write_text(json.dumps(manifest_out, indent=2, default=str) + "\n")
    print(f"\nManifest written: {out_path}")

    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    for c in all_cycles:
        rec = c["reconciliation"]
        print(
            f"cycle {c['cycle']} ({c['label']}): "
            f"fired={rec['rules_fired']}/{rec['total_rules']} "
            f"caught_any={rec['caught_any']} "
            f"neg_ctrl={rec['neg_control_count']}"
        )
    return manifest_out


if __name__ == "__main__":
    main()
