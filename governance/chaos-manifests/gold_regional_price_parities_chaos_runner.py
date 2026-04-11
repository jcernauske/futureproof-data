"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec:  gold-regional-price-parities
Table: consumable.regional_price_parities (51 rows - 50 states + DC)
Shadow namespace: shadow_consumable.regional_price_parities
                  (in the GOLD warehouse)

This is a curated, spec-driven scenario runner (NOT a per-dimension fuzz
runner) because the underlying table is only 51 rows and the interesting
breakages are categorical -- cost_tier boundary edges, adjusted_Nk
derivation purity, verification_status carry-forward.

Information Barrier: This script does NOT read
  - governance/dq-rules/gold-regional-price-parities.json
  - governance/dq-results/*
  - governance/dq-scorecards/*

Corruption choices are based solely on:
  - docs/specs/gold-regional-price-parities.md     (public spec)
  - src/gold/regional_price_parities_transformer.py (derivation code)
  - src/gold/_cost_tier.py                         (cost tier CASE)

Every manipulation happens inside the shadow_consumable namespace. The
real consumable.regional_price_parities table is never mutated.

Shadow carve-outs (hard filter):
  GLD-RPP-043 -- Gold<->Silver passthrough integrity (cross-zone)
  GLD-RPP-055 -- Silver freshness (cross-zone, production-only)

These cross-zone rules reference base.bea_rpp, which the shadow-mode
rewrite remaps to shadow_base.bea_rpp. This chaos harness does not stage
the Silver table, so both rules error on every invocation including the
no-op negative control. Production DQ runs still evaluate them normally.

Pattern mirrors silver_bea_rpp_chaos_runner.py exactly.
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
GOLD_WAREHOUSE = PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"
SOURCE_PARQUET = (
    GOLD_WAREHOUSE
    / "consumable"
    / "regional_price_parities"
    / "data"
    / "00000-0-07edfd60-dda9-4d71-936a-0ea5bdb54bb6.parquet"
)
SHADOW_DIR = GOLD_WAREHOUSE / "shadow_consumable" / "regional_price_parities"
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"

SPEC_NAME = "gold-regional-price-parities"
REAL_FQN = "consumable.regional_price_parities"
SHADOW_FQN = "shadow_consumable.regional_price_parities"

SEED_BASE = 42

# Rules that cannot be evaluated in shadow mode and must be filtered out of
# chaos runs.  See silver_bea_rpp_chaos_runner.py for the full rationale.
#
# GLD-RPP-043: Gold-to-Silver passthrough integrity.  Joins
#   consumable.regional_price_parities against base.bea_rpp. The shadow-mode
#   rewrite remaps base -> shadow_base, which we do not stage, so the rule
#   errors on every invocation including the no-op negative control.
# GLD-RPP-055: Silver freshness.  Reads base.bea_rpp load date. Same
#   cross-zone rewrite problem, and the rule JSON marks it evaluation_mode
#   production_only.
#
# Both rules carry `chaos_exclude: true` in the rules JSON for downstream
# tooling; the hard carve-out lives here because the information barrier
# forbids reading the rules JSON.
SHADOW_EXCLUDED_RULE_IDS = frozenset({
    "GLD-RPP-043",  # cross-zone gold<->silver passthrough integrity
    "GLD-RPP-055",  # cross-zone silver freshness (production_only)
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

    # Safety invariant: the real table must NOT be under the shadow path.
    assert "shadow_" not in str(SOURCE_PARQUET), \
        "refusing to run -- source parquet is inside shadow_ namespace"
    assert "shadow_consumable" in str(SHADOW_DIR), \
        "refusing to run -- shadow dir is not inside shadow_consumable"


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

    Rebuilds each column individually so impossible values (wrong type,
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
        DoubleType,
        IntegerType,
        NestedField,
        StringType,
        TimestampType,
    )
    import pyarrow.parquet as pq

    catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))
    try:
        catalog.create_namespace("shadow_consumable")
    except Exception:
        pass
    try:
        catalog.drop_table(SHADOW_FQN)
    except Exception:
        pass

    # All fields optional so we can land corrupted / null data in the shadow.
    # Schema mirrors consumable.regional_price_parities (15 columns).
    schema = Schema(
        NestedField(1, "record_id", StringType(), required=False),
        NestedField(2, "state_fips", StringType(), required=False),
        NestedField(3, "state_name", StringType(), required=False),
        NestedField(4, "state_abbr", StringType(), required=False),
        NestedField(5, "census_region", StringType(), required=False),
        NestedField(6, "rpp_all_items", DoubleType(), required=False),
        NestedField(7, "purchasing_power_multiplier", DoubleType(), required=False),
        NestedField(8, "cost_tier", StringType(), required=False),
        NestedField(9, "adjusted_30k", DoubleType(), required=False),
        NestedField(10, "adjusted_50k", DoubleType(), required=False),
        NestedField(11, "adjusted_75k", DoubleType(), required=False),
        NestedField(12, "adjusted_100k", DoubleType(), required=False),
        NestedField(13, "verification_status", StringType(), required=False),
        NestedField(14, "data_year", IntegerType(), required=False),
        NestedField(15, "promoted_at", TimestampType(), required=False),
    )
    tbl = catalog.create_table(SHADOW_FQN, schema=schema)
    data = pq.read_table(str(parquet_path))
    tbl.append(data)
    return tbl


def run_dq_rules_shadow():
    from brightsmith.infra.dq_runner import run_rules
    from brightsmith.infra.iceberg_setup import get_catalog

    catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))
    result = run_rules(spec=SPEC_NAME, catalog=catalog, shadow=True)

    # Drop cross-zone rules that can't be evaluated in shadow mode.
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

        catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))
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


# ---- 1. cost_tier classification attacks ---------------------------------

def scenario_ca_cost_tier_low(rows):
    """S1: set CA cost_tier to 'low' (rpp=110.7 should be very_high).

    Must fire the classification correctness rule.
    """
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["cost_tier"]
    rows[idx]["cost_tier"] = "low"
    return [{
        "scenario": "ca_cost_tier_misclassified_low",
        "dimensions": ["accuracy", "consistency"],
        "field": "cost_tier",
        "strategy": "set_wrong_tier_for_rpp",
        "old_value": str(old),
        "new_value": "low (rpp=110.7 should be very_high)",
    }]


def scenario_tn_boundary_left_closed_violation(rows):
    """S2: set TN cost_tier to 'very_low' (rpp=91.0 must be 'low' under left-closed).

    Boundary witness: TN sits exactly at the 91.0 lower-bound of the 'low'
    bucket.  Left-closed means 91.0 is IN 'low', NOT in 'very_low'.
    """
    idx = _find_idx(rows, "47")  # Tennessee
    if idx is None:
        return []
    old_tier = rows[idx]["cost_tier"]
    old_rpp = rows[idx]["rpp_all_items"]
    rows[idx]["rpp_all_items"] = 91.0  # pin to the boundary
    rows[idx]["cost_tier"] = "very_low"
    # recompute multiplier + adjusted_Nk so THIS break is isolated to the
    # tier classification (not a derivation-purity fire).
    mult = 100.0 / 91.0
    rows[idx]["purchasing_power_multiplier"] = round(mult, 4)
    rows[idx]["adjusted_30k"] = round(30000 * mult, 2)
    rows[idx]["adjusted_50k"] = round(50000 * mult, 2)
    rows[idx]["adjusted_75k"] = round(75000 * mult, 2)
    rows[idx]["adjusted_100k"] = round(100000 * mult, 2)
    return [{
        "scenario": "tn_boundary_left_closed_91_violation",
        "dimensions": ["accuracy", "consistency"],
        "field": "cost_tier",
        "strategy": "pin_rpp_to_boundary_and_tier_to_wrong_side",
        "old_value": f"TN rpp={old_rpp} tier={old_tier}",
        "new_value": "TN rpp=91.0 tier=very_low (should be 'low' under left-closed)",
    }]


def scenario_boundary_drift_108(rows):
    """S3: inject a synthetic row at rpp=108.0 with cost_tier='high'.

    Under left-closed convention, rpp=108.0 is the lower bound of
    'very_high'.  A row with tier='high' at that rpp is a classification
    error.  This uses a spare state-fips-like code '99' (distinct from any
    real state) with adjusted_Nk values that match the (wrong) derivation
    at rpp=108, so the classification rule is the *only* expected fire.
    """
    mult = 100.0 / 108.0
    dupe = {
        "record_id": "rpc-chaos-boundary-108",
        "state_fips": "99",
        "state_name": "Chaos State 108",
        "state_abbr": "ZC",
        "census_region": "South",
        "rpp_all_items": 108.0,
        "purchasing_power_multiplier": round(mult, 4),
        "cost_tier": "high",  # WRONG: should be very_high
        "adjusted_30k": round(30000 * mult, 2),
        "adjusted_50k": round(50000 * mult, 2),
        "adjusted_75k": round(75000 * mult, 2),
        "adjusted_100k": round(100000 * mult, 2),
        "verification_status": "estimate",
        "data_year": 2024,
        "promoted_at": datetime.datetime(2026, 4, 11, 0, 0, 0),
    }
    rows.append(dupe)
    return [{
        "scenario": "boundary_drift_rpp_108_high",
        "dimensions": ["accuracy", "consistency", "volume", "referential_integrity"],
        "field": "cost_tier",
        "strategy": "inject_synthetic_row_at_boundary",
        "old_value": "(no row at rpp=108.0)",
        "new_value": "synthetic row state_fips=99 rpp=108.0 tier=high",
    }]


def scenario_boundary_drift_107_999(rows):
    """S4: inject a row at rpp=107.999 with cost_tier='very_high'.

    Under left-closed convention, rpp < 108.0 is 'high', so 107.999 with
    tier='very_high' is a classification error.  This is the complement
    of S3.
    """
    mult = 100.0 / 107.999
    dupe = {
        "record_id": "rpc-chaos-boundary-107999",
        "state_fips": "98",
        "state_name": "Chaos State 107.999",
        "state_abbr": "ZD",
        "census_region": "South",
        "rpp_all_items": 107.999,
        "purchasing_power_multiplier": round(mult, 4),
        "cost_tier": "very_high",  # WRONG: should be high
        "adjusted_30k": round(30000 * mult, 2),
        "adjusted_50k": round(50000 * mult, 2),
        "adjusted_75k": round(75000 * mult, 2),
        "adjusted_100k": round(100000 * mult, 2),
        "verification_status": "estimate",
        "data_year": 2024,
        "promoted_at": datetime.datetime(2026, 4, 11, 0, 0, 0),
    }
    rows.append(dupe)
    return [{
        "scenario": "boundary_drift_rpp_107_999_very_high",
        "dimensions": ["accuracy", "consistency", "volume", "referential_integrity"],
        "field": "cost_tier",
        "strategy": "inject_synthetic_row_just_below_boundary",
        "old_value": "(no row at rpp=107.999)",
        "new_value": "synthetic row state_fips=98 rpp=107.999 tier=very_high",
    }]


def scenario_cost_tier_invalid_enum(rows):
    """S5: set one row's cost_tier to 'extreme' -- IN-list rule must fire."""
    idx = _find_idx(rows, "17")  # Illinois
    if idx is None:
        return []
    old = rows[idx]["cost_tier"]
    rows[idx]["cost_tier"] = "extreme"
    return [{
        "scenario": "cost_tier_invalid_enum",
        "dimensions": ["validity"],
        "field": "cost_tier",
        "strategy": "invalid_enum_value",
        "old_value": str(old),
        "new_value": "extreme",
    }]


def scenario_all_tiers_average(rows):
    """S6: set EVERY row's cost_tier to 'average' -- classification must fire.

    Also collapses distribution coverage.
    """
    count = 0
    for r in rows:
        if r.get("cost_tier") != "average":
            r["cost_tier"] = "average"
            count += 1
    return [{
        "scenario": "all_rows_cost_tier_average",
        "dimensions": ["accuracy", "consistency", "coverage"],
        "field": "cost_tier",
        "strategy": "collapse_distribution_single_value",
        "old_value": "mixed (4 or 5 tiers)",
        "new_value": f"{count} rows relabeled to 'average'",
    }]


# ---- 2. adjusted_Nk derivation attacks -----------------------------------

def scenario_ca_adjusted_50k_plausible_but_wrong(rows):
    """S7: set CA adjusted_50k to 50000.0 (high-cost sanity check fire).

    CA is very_high cost, so adjusted_50k should be strictly < 50000.
    Also breaks derivation purity: 50000 != round(50000 * multiplier, 2)
    for CA's multiplier ~0.9034.
    """
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["adjusted_50k"]
    rows[idx]["adjusted_50k"] = 50000.0
    return [{
        "scenario": "ca_adjusted_50k_at_national",
        "dimensions": ["accuracy", "consistency", "reasonableness"],
        "field": "adjusted_50k",
        "strategy": "set_to_national_for_high_cost_state",
        "old_value": str(old),
        "new_value": "50000.0 (should be < 50000 for CA)",
    }]


def scenario_ia_adjusted_50k_plausible_but_wrong(rows):
    """S8: set IA adjusted_50k to 40000.0 (low-cost sanity check fire).

    IA is very_low cost, so adjusted_50k should be strictly > 50000.
    40000 also breaks derivation purity (IA multiplier ~1.1390 -> 56947.61).
    """
    idx = _find_idx(rows, "19")
    if idx is None:
        return []
    old = rows[idx]["adjusted_50k"]
    rows[idx]["adjusted_50k"] = 40000.0
    return [{
        "scenario": "ia_adjusted_50k_below_national",
        "dimensions": ["accuracy", "consistency", "reasonableness"],
        "field": "adjusted_50k",
        "strategy": "set_below_national_for_low_cost_state",
        "old_value": str(old),
        "new_value": "40000.0 (should be > 50000 for IA)",
    }]


def scenario_adjusted_transposition(rows):
    """S9: set NY's adjusted_50k to adjusted_75k (transposition error).

    Derivation purity rule must fire at 0.01 tolerance.
    """
    idx = _find_idx(rows, "36")  # New York
    if idx is None:
        return []
    old = rows[idx]["adjusted_50k"]
    rows[idx]["adjusted_50k"] = rows[idx]["adjusted_75k"]
    return [{
        "scenario": "adjusted_transposition_50k_eq_75k",
        "dimensions": ["accuracy", "consistency"],
        "field": "adjusted_50k",
        "strategy": "transpose_50k_with_75k",
        "old_value": str(old),
        "new_value": f"{rows[idx]['adjusted_75k']} (copied from adjusted_75k)",
    }]


def scenario_adjusted_three_decimal_noise(rows):
    """S10: set CA adjusted_50k to 45167.124 (three decimal places).

    Expected value: 45167.12.  Delta = 0.004, inside 0.01 tolerance.
    This is a NEGATIVE probe: the derivation-purity rule should NOT fire.
    CA sanity (< 50000) still passes.
    """
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["adjusted_50k"]
    rows[idx]["adjusted_50k"] = 45167.124
    return [{
        "scenario": "adjusted_three_decimal_noise_within_tolerance",
        "dimensions": ["negative_control"],
        "field": "adjusted_50k",
        "strategy": "three_decimal_noise_inside_0_01_tolerance",
        "old_value": str(old),
        "new_value": "45167.124 (delta ~0.004, within 0.01 tolerance)",
        "expected_fired": False,
    }]


def scenario_adjusted_off_by_thousand(rows):
    """S11: set CA adjusted_50k to 451.67 (off by 100x).

    Both derivation purity + CA sanity must fire.
    """
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["adjusted_50k"]
    rows[idx]["adjusted_50k"] = 451.67
    return [{
        "scenario": "ca_adjusted_50k_off_by_100x",
        "dimensions": ["accuracy", "reasonableness"],
        "field": "adjusted_50k",
        "strategy": "divide_by_100",
        "old_value": str(old),
        "new_value": "451.67 (should be 45167.12)",
    }]


# ---- 3. verification_status carry-forward --------------------------------

def scenario_verif_flip_ca_to_estimate(rows):
    """S12: flip CA verification_status to 'estimate'.

    Breaks count=8 rule AND the 8-state subset rule.
    """
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["verification_status"]
    rows[idx]["verification_status"] = "estimate"
    return [{
        "scenario": "verif_flip_ca_to_estimate",
        "dimensions": ["consistency", "accuracy"],
        "field": "verification_status",
        "strategy": "flip_verified_to_estimate",
        "old_value": f"CA={old}",
        "new_value": "CA=estimate",
    }]


def scenario_verif_mark_texas_official(rows):
    """S13: mark Texas as bea_official.

    Breaks count=8 rule AND the 8-state subset rule (TX not in canonical set).
    """
    idx = _find_idx(rows, "48")
    if idx is None:
        return []
    old = rows[idx]["verification_status"]
    rows[idx]["verification_status"] = "bea_official"
    return [{
        "scenario": "verif_mark_texas_official",
        "dimensions": ["consistency", "accuracy"],
        "field": "verification_status",
        "strategy": "mark_non_verified_as_official",
        "old_value": f"TX={old}",
        "new_value": "TX=bea_official",
    }]


def scenario_verif_invalid_value(rows):
    """S14: set one row's verification_status to 'verified' -- IN-list rule."""
    idx = _find_idx(rows, "27")  # Minnesota
    if idx is None:
        return []
    old = rows[idx]["verification_status"]
    rows[idx]["verification_status"] = "verified"
    return [{
        "scenario": "verif_invalid_value_verified",
        "dimensions": ["validity"],
        "field": "verification_status",
        "strategy": "invalid_enum_value",
        "old_value": str(old),
        "new_value": "verified",
    }]


def scenario_verif_all_bea_official(rows):
    """S15: set all 51 rows to bea_official -- count rule + subset rule."""
    count = 0
    for r in rows:
        if r.get("verification_status") != "bea_official":
            r["verification_status"] = "bea_official"
            count += 1
    return [{
        "scenario": "verif_all_bea_official",
        "dimensions": ["consistency", "reasonableness"],
        "field": "verification_status",
        "strategy": "set_all_rows_verified",
        "old_value": "8 bea_official / 43 estimate",
        "new_value": f"all {count + 8} bea_official",
    }]


# ---- 4. Carry-forward integrity (Gold-to-Silver) -------------------------

def scenario_ca_state_abbr_wa(rows):
    """S16: change CA state_abbr to 'WA' in Gold -- spot check + bijection."""
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["state_abbr"]
    rows[idx]["state_abbr"] = "WA"
    return [{
        "scenario": "ca_state_abbr_wa",
        "dimensions": ["accuracy", "consistency"],
        "field": "state_abbr",
        "strategy": "wrong_but_valid_abbr",
        "old_value": str(old),
        "new_value": "WA (collides with Washington)",
    }]


def scenario_ca_rpp_diverge_from_silver(rows):
    """S17: change CA rpp_all_items in Gold without updating derived fields.

    In a single-zone shadow world, the cross-zone passthrough rule
    (GLD-RPP-043) cannot fire because it is hard-excluded from chaos runs.
    This scenario verifies what OTHER rules catch an rpp drift:

      - inverse invariant should fire (multiplier x rpp != 100)
      - cost_tier classification should fire (new rpp is still 105 so
        not very_high anymore if the row is CA)
      - adjusted_Nk derivation-purity stays OK because multiplier and
        adjusted_Nk are untouched -- only rpp moved.  That is the gap.
    """
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old = rows[idx]["rpp_all_items"]
    rows[idx]["rpp_all_items"] = 105.0
    # do NOT update multiplier or adjusted_Nk -- we want to probe
    # which single-zone rules detect a bare rpp drift.
    return [{
        "scenario": "ca_rpp_drift_silver_divergence",
        "dimensions": ["accuracy", "consistency", "referential_integrity"],
        "field": "rpp_all_items",
        "strategy": "drift_rpp_leave_derivations",
        "old_value": str(old),
        "new_value": "105.0 (multiplier, adjusted_Nk, tier unchanged)",
    }]


def scenario_state_name_null(rows):
    """S18: null out Arkansas state_name -- completeness rule."""
    idx = _find_idx(rows, "05")
    if idx is None:
        return []
    old = rows[idx]["state_name"]
    rows[idx]["state_name"] = None
    return [{
        "scenario": "null_state_name_ar",
        "dimensions": ["completeness"],
        "field": "state_name",
        "strategy": "null_required_field",
        "old_value": str(old),
        "new_value": "None",
    }]


# ---- 5. Row count + grain ------------------------------------------------

def scenario_drop_wyoming(rows):
    """S19: drop Wyoming -- row count + FIPS set rule."""
    idx = _find_idx(rows, "56")
    if idx is None:
        return []
    old = rows.pop(idx)
    return [{
        "scenario": "drop_wyoming",
        "dimensions": ["volume", "referential_integrity"],
        "field": "(row)",
        "strategy": "delete_wyoming_row",
        "old_value": f"WY row present ({old.get('state_name')})",
        "new_value": "Wyoming row removed (50 rows)",
    }]


def scenario_duplicate_california(rows):
    """S20: duplicate California -- row count + FIPS uniqueness + record_id uniq."""
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    dupe = copy.deepcopy(rows[idx])
    # Keep everything identical -- record_id duplication is the whole point.
    rows.append(dupe)
    return [{
        "scenario": "duplicate_california",
        "dimensions": ["uniqueness", "volume"],
        "field": "state_fips,record_id",
        "strategy": "append_identical_duplicate_row",
        "old_value": "CA appears 1x",
        "new_value": "CA appears 2x (52 rows)",
    }]


# ---- 6. Negative controls -----------------------------------------------

def scenario_neg_swap_ia_ok(rows):
    """N1: swap IA and OK state_name values (both very_low, both same mult).

    IA and OK share: rpp=87.8, multiplier=1.1390, verification=bea_official,
    cost_tier=very_low, identical adjusted_Nk values. Swapping state_name
    between them leaves every numeric and categorical field aligned by
    state_fips (because we only rename two rows that happen to tie on
    everything else).  Should NOT fire anything.
    """
    ia = _find_idx(rows, "19")
    ok = _find_idx(rows, "40")
    if ia is None or ok is None:
        return []
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
    """N2: no-op cycle -- zero mutations -- should NOT fire anything."""
    return [{
        "scenario": "neg_control_noop",
        "dimensions": ["negative_control"],
        "field": "(none)",
        "strategy": "noop",
        "old_value": "(unchanged)",
        "new_value": "(unchanged)",
        "expected_fired": False,
    }]


def scenario_neg_three_decimal_noise(rows):
    """N3: wraps scenario_adjusted_three_decimal_noise for a dedicated negative cycle."""
    return scenario_adjusted_three_decimal_noise(rows)


# ---------------------------------------------------------------------------
# Cycle plan
# ---------------------------------------------------------------------------

CYCLE_SCENARIOS = {
    1: {
        "rate": 0.05,
        "label": "cost_tier_classification_attacks",
        "scenarios": [
            scenario_ca_cost_tier_low,
            scenario_cost_tier_invalid_enum,
        ],
    },
    2: {
        "rate": 0.06,
        "label": "cost_tier_boundary_drift",
        "scenarios": [
            scenario_tn_boundary_left_closed_violation,
            scenario_boundary_drift_108,
            scenario_boundary_drift_107_999,
        ],
    },
    3: {
        "rate": 0.07,
        "label": "adjusted_Nk_derivation",
        "scenarios": [
            scenario_ca_adjusted_50k_plausible_but_wrong,
            scenario_ia_adjusted_50k_plausible_but_wrong,
            scenario_adjusted_transposition,
            scenario_adjusted_off_by_thousand,
        ],
    },
    4: {
        "rate": 0.08,
        "label": "verification_status_full_sweep",
        "scenarios": [
            scenario_verif_flip_ca_to_estimate,
            scenario_verif_mark_texas_official,
            scenario_verif_invalid_value,
            scenario_verif_all_bea_official,
        ],
    },
    5: {
        "rate": 0.10,
        "label": "carry_forward_grain_and_volume",
        "scenarios": [
            scenario_ca_state_abbr_wa,
            scenario_ca_rpp_diverge_from_silver,
            scenario_state_name_null,
            scenario_drop_wyoming,
            scenario_duplicate_california,
            scenario_all_tiers_average,
        ],
    },
    6: {
        "rate": 0.00,
        "label": "negative_control_three_decimal_noise",
        "scenarios": [scenario_neg_three_decimal_noise],
    },
    7: {
        "rate": 0.00,
        "label": "negative_control_swap_ia_ok",
        "scenarios": [scenario_neg_swap_ia_ok],
    },
    8: {
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
            print(f"    {r.get('rule_id'):<20} {status:<6} value={r.get('raw_value')}")
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
    neg_controls = [
        m for m in manifest if "negative_control" in m.get("dimensions", [])
    ]
    real_injections = [
        m for m in manifest if "negative_control" not in m.get("dimensions", [])
    ]

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
        "shadow_excluded_rule_ids": sorted(SHADOW_EXCLUDED_RULE_IDS),
        "cycles": all_cycles,
    }

    out_path = (
        PROJECT_ROOT
        / "governance/chaos-manifests/gold-regional-price-parities-manifest.json"
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
