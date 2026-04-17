"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner (SILVER ZONE)
Spec: silver-base-college-scorecard-institution
Table: base.college_scorecard_institution (shadow_base.* when running)

Injects corruptions across all 10 DQ dimensions, targeting the 17 SLV-CSI-*
rules that guard the Silver base table. Writes a shadow Iceberg table,
executes DQ rules with --shadow, and records what fired vs what stayed silent.

Information barrier: This runner does NOT read DQ rule definitions
(governance/dq-rules/silver-base-college-scorecard-institution.json) nor
the scorecard artifacts. It targets the 14 user-specified corruption
scenarios that map to rules SLV-CSI-001 through SLV-CSI-017 by description.
"""

from __future__ import annotations

import copy
import datetime
import json
import random
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
SAMPLE_CSV = PROJECT_ROOT / "tests/raw/college_scorecard_institution_sample.csv"

# Silver-zone iceberg warehouse (transformer writes here; we write shadow here too)
SILVER_WAREHOUSE_PATH = PROJECT_ROOT / "data/silver/iceberg_warehouse"
# Shared catalog across zones
CATALOG_PATH = PROJECT_ROOT / "data/catalog/catalog.db"
SHADOW_DIR = SILVER_WAREHOUSE_PATH / "shadow_base/college_scorecard_institution"

MANIFEST_PATH = (
    PROJECT_ROOT
    / "governance/chaos-manifests/silver-base-college-scorecard-institution-manifest.json"
)
REPORT_PATH = (
    PROJECT_ROOT
    / "governance/chaos-manifests/silver-base-college-scorecard-institution-chaos.md"
)

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42
TARGET_ROW_COUNT = 3039  # Silver baseline: 3,039 rows (matches Bronze 1:1)

# Institution control integer -> Silver string label
CONTROL_LABELS = {1: "Public", 2: "Private nonprofit", 3: "Private for-profit"}

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR",
]


# ---------------------------------------------------------------------------
# Silver-shaped row generation
# ---------------------------------------------------------------------------


def _compute_record_id(unitid: int) -> str:
    """Compute deterministic record_id using the same prefix ('csi') and
    hash as the Silver transformer (see compute_grain_id in brightsmith)."""
    import hashlib

    grain = f"{unitid}"
    h = hashlib.sha256(grain.encode()).hexdigest()[:16]
    return f"csi-{h}"


def _build_silver_row(
    unitid: int,
    instnm: str,
    stabbr: str,
    control: int,
    rng: random.Random,
    today: datetime.date,
    now: datetime.datetime,
) -> dict:
    """Build one clean Silver-shaped row for the given control type."""
    if control == 1:  # Public
        coa = max(5000.0, rng.gauss(25000, 5000))
        np_annual = coa * rng.uniform(0.45, 0.75)
        # Quintiles Q1..Q5: Q1 cheapest, Q5 most expensive
        q1 = np_annual * rng.uniform(0.35, 0.55)
        q2 = q1 * rng.uniform(1.10, 1.35)
        q3 = q2 * rng.uniform(1.10, 1.35)
        q4 = q3 * rng.uniform(1.10, 1.35)
        q5 = q4 * rng.uniform(1.10, 1.35)
        npt4_pub_raw, npt4_priv_raw = np_annual, None
        npt_q_pub = [q1, q2, q3, q4, q5]
        npt_q_priv = [None] * 5
        tuition_in = max(1000.0, coa * rng.uniform(0.30, 0.50))
        tuition_out = tuition_in * rng.uniform(1.8, 2.8)
        roomboard_on = max(4000.0, rng.gauss(9000, 2000))
        roomboard_off = max(4000.0, rng.gauss(8500, 2000))
        booksupply = max(400.0, rng.gauss(1200, 300))
        costt4_a_raw, costt4_p_raw = coa, None
    elif control == 2:  # Private nonprofit
        coa = max(10000.0, rng.gauss(42000, 10000))
        np_annual = coa * rng.uniform(0.40, 0.70)
        q1 = np_annual * rng.uniform(0.30, 0.50)
        q2 = q1 * rng.uniform(1.10, 1.35)
        q3 = q2 * rng.uniform(1.10, 1.35)
        q4 = q3 * rng.uniform(1.10, 1.35)
        q5 = q4 * rng.uniform(1.10, 1.35)
        npt4_pub_raw, npt4_priv_raw = None, np_annual
        npt_q_pub = [None] * 5
        npt_q_priv = [q1, q2, q3, q4, q5]
        tuition_in = max(8000.0, rng.gauss(35000, 8000))
        tuition_out = tuition_in
        roomboard_on = max(5000.0, rng.gauss(12000, 3000))
        roomboard_off = max(5000.0, rng.gauss(11000, 3000))
        booksupply = max(500.0, rng.gauss(1200, 300))
        costt4_a_raw, costt4_p_raw = coa, None
    else:  # For-profit (3)
        coa = max(10000.0, rng.gauss(30000, 8000))
        np_annual = coa * rng.uniform(0.60, 0.90)
        # For-profit often lacks full quintile coverage -- simulate sparseness
        q1 = np_annual * rng.uniform(0.40, 0.60) if rng.random() < 0.5 else None
        q2 = (q1 * rng.uniform(1.10, 1.35)) if (q1 is not None and rng.random() < 0.5) else None
        q3 = None
        q4 = None
        q5 = (np_annual * rng.uniform(1.10, 1.40)) if rng.random() < 0.5 else None
        npt4_pub_raw, npt4_priv_raw = None, np_annual
        npt_q_pub = [None] * 5
        npt_q_priv = [q1, q2, q3, q4, q5]
        tuition_in = max(5000.0, rng.gauss(15000, 4000))
        tuition_out = tuition_in
        roomboard_on = None
        roomboard_off = max(5000.0, rng.gauss(9000, 2000))
        booksupply = max(400.0, rng.gauss(1000, 200))
        costt4_a_raw, costt4_p_raw = None, coa

    institution_control = CONTROL_LABELS[control]

    # Randomly null out net price annual (~26% missing overall per Bronze EDA)
    # but only for non-public, to keep public coverage high
    missing_np = rng.random() < 0.25 and control != 1
    if missing_np:
        np_annual = None
        q1 = q2 = q3 = q4 = q5 = None
        coa_is_null = rng.random() < 0.3
        if coa_is_null:
            coa = None

    coa_annual = coa
    coa_4yr = coa * 4 if coa is not None else None
    np_4yr = np_annual * 4 if np_annual is not None else None

    # Quintile values that flow into the Silver unified quintile columns
    if control == 1:
        silver_q = list(npt_q_pub)
    else:
        silver_q = list(npt_q_priv)
    if missing_np:
        silver_q = [None] * 5

    record = {
        "record_id": _compute_record_id(unitid),
        "unitid": unitid,
        "institution_name": instnm,
        "state_abbr": stabbr,
        "institution_control": institution_control,
        "cost_of_attendance_annual": coa_annual,
        "cost_of_attendance_4yr": coa_4yr,
        "net_price_annual": np_annual,
        "net_price_4yr": np_4yr,
        "net_price_q1": silver_q[0],
        "net_price_q2": silver_q[1],
        "net_price_q3": silver_q[2],
        "net_price_q4": silver_q[3],
        "net_price_q5": silver_q[4],
        "tuition_in_state": tuition_in,
        "tuition_out_of_state": tuition_out,
        "room_board_on_campus": roomboard_on,
        "room_board_off_campus": roomboard_off,
        "books_supplies": booksupply,
        "costt4_a_raw": costt4_a_raw,
        "costt4_p_raw": costt4_p_raw,
        "npt4_pub_raw": npt4_pub_raw,
        "npt4_priv_raw": npt4_priv_raw,
        "npt41_pub_raw": npt_q_pub[0],
        "npt42_pub_raw": npt_q_pub[1],
        "npt43_pub_raw": npt_q_pub[2],
        "npt44_pub_raw": npt_q_pub[3],
        "npt45_pub_raw": npt_q_pub[4],
        "npt41_priv_raw": npt_q_priv[0],
        "npt42_priv_raw": npt_q_priv[1],
        "npt43_priv_raw": npt_q_priv[2],
        "npt44_priv_raw": npt_q_priv[3],
        "npt45_priv_raw": npt_q_priv[4],
        "source_load_date": today,
        "ingested_at": now,
    }
    return record


def generate_clean_silver_data(rng: random.Random) -> list[dict]:
    """Produce ~3,039 clean Silver-shaped rows with realistic control mix.

    Distribution targets the SLV-CSI-012/013/014 coverage thresholds
    comfortably (public ~88-90%, private-nonprofit ~70-72%, for-profit ~52-55%).
    """
    rows: list[dict] = []
    used_unitids: set[int] = set()
    today = datetime.date.today()
    # Silver Iceberg TimestampType is naive (no tz); match that.
    now = datetime.datetime.utcnow().replace(microsecond=0)

    prefixes = ["University of", "State University at", "College of",
                "Institute of Technology", "Polytechnic University of"]
    suffixes = ["Sciences", "Arts", "Engineering", "Medicine", "Business",
                "Education", "Agriculture", "Technology", "Liberal Arts"]
    cities = ["Springfield", "Riverside", "Fairview", "Georgetown", "Madison",
              "Monroe", "Franklin", "Clinton", "Jackson", "Lincoln",
              "Salem", "Bristol", "Chester", "Dover", "Oxford",
              "Cambridge", "Hartford", "Burlington", "Portland", "Asheville"]

    while len(rows) < TARGET_ROW_COUNT:
        unitid = rng.randint(100000, 999999)
        while unitid in used_unitids:
            unitid = rng.randint(100000, 999999)
        used_unitids.add(unitid)

        roll = rng.random()
        if roll < 0.285:   # ~867 public
            control = 1
        elif roll < 0.862: # ~1,754 private nonprofit
            control = 2
        else:              # ~418 for-profit
            control = 3

        state = rng.choice(US_STATES)
        style = rng.choice(["prefix_state", "city_college", "name_university"])
        if style == "prefix_state":
            name = f"{rng.choice(prefixes)} {state} - {rng.choice(suffixes)}"
        elif style == "city_college":
            name = f"{rng.choice(cities)} {rng.choice(['College', 'University', 'Institute'])}"
        else:
            name = f"{rng.choice(cities)} {rng.choice(suffixes)} University"

        rows.append(_build_silver_row(unitid, name, state, control, rng, today, now))

    return rows


# ---------------------------------------------------------------------------
# Corruption strategies — each returns a list of manifest entries
# ---------------------------------------------------------------------------


def _pick_indices(rows: list[dict], indices: list[int], rng: random.Random,
                  divisor: int = 3, lo: int = 1) -> list[int]:
    """Sample a subset of indices (at most len(indices)//divisor, min lo)."""
    n = max(lo, len(indices) // divisor)
    return rng.sample(list(indices), min(len(indices), n))


def corrupt_uniqueness(rows, indices, rng):
    """Scenario 1: Duplicate record_id / unitid --> SLV-CSI-002, SLV-CSI-003."""
    manifest = []
    n_dupes = max(5, len(indices) // 4)
    source_idxs = rng.sample(range(len(rows)), min(n_dupes, len(rows)))
    for src in source_idxs:
        dupe = copy.deepcopy(rows[src])
        # Keep same unitid AND record_id to fire both rules
        dupe["institution_name"] = f"{dupe['institution_name']} [dup]"
        pos = len(rows)
        rows.append(dupe)
        manifest.append({
            "row": pos, "dimension": "uniqueness",
            "field": "record_id,unitid",
            "strategy": "duplicate_grain",
            "target_rules": ["SLV-CSI-002", "SLV-CSI-003"],
            "old_value": f"none (new row copy of row {src})",
            "new_value": f"unitid={dupe['unitid']},record_id={dupe['record_id']}",
        })
    return manifest


def corrupt_validity(rows, indices, rng):
    """Scenario 2: Invalid institution_control label --> SLV-CSI-005."""
    manifest = []
    targets = _pick_indices(rows, indices, rng, divisor=3)
    bad_labels = ["public", "PRIVATE", "For Profit", "Unknown", "Other",
                  "Community", "Trade School", "XYZ", ""]
    for i in targets:
        old = rows[i]["institution_control"]
        new = rng.choice(bad_labels)
        rows[i]["institution_control"] = new
        manifest.append({
            "row": i, "dimension": "validity", "field": "institution_control",
            "strategy": "bad_control_label",
            "target_rules": ["SLV-CSI-005"],
            "old_value": str(old), "new_value": str(new),
        })
    return manifest


def corrupt_completeness(rows, indices, rng):
    """Scenarios 3 & 14: Null institution_control --> SLV-CSI-006,
    Null record_id --> SLV-CSI-004."""
    manifest = []
    targets = _pick_indices(rows, indices, rng, divisor=3)
    for i in targets:
        strategy = rng.choice(["null_control", "null_record_id"])
        if strategy == "null_control":
            old = rows[i]["institution_control"]
            rows[i]["institution_control"] = None
            manifest.append({
                "row": i, "dimension": "completeness",
                "field": "institution_control",
                "strategy": strategy,
                "target_rules": ["SLV-CSI-006"],
                "old_value": str(old), "new_value": "null",
            })
        else:  # null_record_id
            old = rows[i]["record_id"]
            rows[i]["record_id"] = None
            manifest.append({
                "row": i, "dimension": "completeness",
                "field": "record_id",
                "strategy": strategy,
                "target_rules": ["SLV-CSI-004"],
                "old_value": str(old), "new_value": "null",
            })
    return manifest


def corrupt_consistency(rows, indices, rng):
    """Scenario 4: net_price_annual > cost_of_attendance_annual --> SLV-CSI-007.
    Scenario 5: 4yr != annual * 4 --> SLV-CSI-008, SLV-CSI-009."""
    manifest = []
    targets = _pick_indices(rows, indices, rng, divisor=3)
    for i in targets:
        strategy = rng.choice(["np_gt_coa", "break_np_4yr_tautology",
                               "break_coa_4yr_tautology"])
        if strategy == "np_gt_coa":
            coa = rows[i].get("cost_of_attendance_annual")
            if coa is None or coa <= 0:
                # Force COA to be meaningful and np above it
                coa = 20000.0
                rows[i]["cost_of_attendance_annual"] = coa
                rows[i]["cost_of_attendance_4yr"] = coa * 4
            old_np = rows[i].get("net_price_annual")
            new_np = coa * rng.uniform(1.10, 1.40)
            rows[i]["net_price_annual"] = new_np
            rows[i]["net_price_4yr"] = new_np * 4
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "net_price_annual,cost_of_attendance_annual",
                "strategy": strategy,
                "target_rules": ["SLV-CSI-007"],
                "old_value": f"np={old_np},coa={coa}",
                "new_value": f"np={new_np:.2f},coa={coa:.2f}",
            })
        elif strategy == "break_np_4yr_tautology":
            np_annual = rows[i].get("net_price_annual")
            if np_annual is None:
                # Force a value to make the rule applicable
                np_annual = 15000.0
                rows[i]["net_price_annual"] = np_annual
            old_4yr = rows[i].get("net_price_4yr")
            # Make 4yr wrong by a dollar amount well above 0.01 tolerance
            new_4yr = np_annual * 4 + rng.uniform(10.0, 500.0)
            rows[i]["net_price_4yr"] = new_4yr
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "net_price_4yr,net_price_annual",
                "strategy": strategy,
                "target_rules": ["SLV-CSI-008"],
                "old_value": f"annual={np_annual},4yr={old_4yr}",
                "new_value": f"annual={np_annual},4yr={new_4yr:.2f}",
            })
        else:  # break_coa_4yr_tautology
            coa_annual = rows[i].get("cost_of_attendance_annual")
            if coa_annual is None:
                coa_annual = 25000.0
                rows[i]["cost_of_attendance_annual"] = coa_annual
            old_4yr = rows[i].get("cost_of_attendance_4yr")
            new_4yr = coa_annual * 4 - rng.uniform(10.0, 500.0)
            rows[i]["cost_of_attendance_4yr"] = new_4yr
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "cost_of_attendance_4yr,cost_of_attendance_annual",
                "strategy": strategy,
                "target_rules": ["SLV-CSI-009"],
                "old_value": f"annual={coa_annual},4yr={old_4yr}",
                "new_value": f"annual={coa_annual},4yr={new_4yr:.2f}",
            })
    return manifest


def corrupt_coverage(rows, indices, rng):
    """Scenarios 6-9: Drop various coverage rates.

    Strategies applied in separate passes so each cycle's rate (5-10%) is
    respected for the overall coverage rule but each dimension still gets
    exercised.
    """
    manifest = []

    # Scenario 6a: Drop overall net_price_annual coverage below 70% -> SLV-CSI-010
    populated_np = [i for i in range(len(rows)) if rows[i].get("net_price_annual") is not None]
    n_drop_overall = int(len(populated_np) * 0.10)
    for i in rng.sample(populated_np, min(n_drop_overall, len(populated_np))):
        old = rows[i]["net_price_annual"]
        rows[i]["net_price_annual"] = None
        rows[i]["net_price_4yr"] = None
        manifest.append({
            "row": i, "dimension": "coverage",
            "field": "net_price_annual",
            "strategy": "null_np_overall",
            "target_rules": ["SLV-CSI-010"],
            "old_value": str(old), "new_value": "null",
        })

    # Scenario 6b: Drop overall cost_of_attendance_annual coverage below 70% -> SLV-CSI-011.
    # Baseline COA coverage is ~95% (COA populated for essentially every row
    # except the occasional missing_np fork); to push overall coverage below
    # 70%, we must null ~30% of populated COA rows.
    populated_coa = [i for i in range(len(rows))
                     if rows[i].get("cost_of_attendance_annual") is not None]
    n_drop_coa = int(len(populated_coa) * 0.32)
    for i in rng.sample(populated_coa, min(n_drop_coa, len(populated_coa))):
        old = rows[i]["cost_of_attendance_annual"]
        rows[i]["cost_of_attendance_annual"] = None
        rows[i]["cost_of_attendance_4yr"] = None
        manifest.append({
            "row": i, "dimension": "coverage",
            "field": "cost_of_attendance_annual",
            "strategy": "null_coa_overall",
            "target_rules": ["SLV-CSI-011"],
            "old_value": str(old), "new_value": "null",
        })

    # Scenario 7: Drop PUBLIC (control=1) net_price_annual coverage below 85%
    # Baseline public coverage ~89.3%. Null ~8% of public populated rows.
    pub_populated = [i for i in range(len(rows))
                     if rows[i].get("institution_control") == "Public"
                     and rows[i].get("net_price_annual") is not None]
    n_drop_pub = int(len(pub_populated) * 0.08)
    for i in rng.sample(pub_populated, min(n_drop_pub, len(pub_populated))):
        old = rows[i]["net_price_annual"]
        rows[i]["net_price_annual"] = None
        rows[i]["net_price_4yr"] = None
        manifest.append({
            "row": i, "dimension": "coverage",
            "field": "net_price_annual",
            "strategy": "null_np_public",
            "target_rules": ["SLV-CSI-012"],
            "old_value": str(old), "new_value": "null",
        })

    # Scenario 8: Drop PRIVATE NONPROFIT (control=2) net_price_annual coverage below 65%
    # Baseline ~70.6%. Null ~10% of private populated rows.
    priv_populated = [i for i in range(len(rows))
                      if rows[i].get("institution_control") == "Private nonprofit"
                      and rows[i].get("net_price_annual") is not None]
    n_drop_priv = int(len(priv_populated) * 0.10)
    for i in rng.sample(priv_populated, min(n_drop_priv, len(priv_populated))):
        old = rows[i]["net_price_annual"]
        rows[i]["net_price_annual"] = None
        rows[i]["net_price_4yr"] = None
        manifest.append({
            "row": i, "dimension": "coverage",
            "field": "net_price_annual",
            "strategy": "null_np_private_nonprofit",
            "target_rules": ["SLV-CSI-013"],
            "old_value": str(old), "new_value": "null",
        })

    # Scenario 9: Drop FOR-PROFIT (control=3) net_price_annual coverage below 50%.
    # The for-profit baseline varies; aggressively null 60% of populated rows
    # in this subgroup to reliably push below the 50% threshold regardless of
    # starting baseline.
    forp_populated = [i for i in range(len(rows))
                      if rows[i].get("institution_control") == "Private for-profit"
                      and rows[i].get("net_price_annual") is not None]
    n_drop_fp = int(len(forp_populated) * 0.60)
    for i in rng.sample(forp_populated, min(n_drop_fp, len(forp_populated))):
        old = rows[i]["net_price_annual"]
        rows[i]["net_price_annual"] = None
        rows[i]["net_price_4yr"] = None
        manifest.append({
            "row": i, "dimension": "coverage",
            "field": "net_price_annual",
            "strategy": "null_np_for_profit",
            "target_rules": ["SLV-CSI-014"],
            "old_value": str(old), "new_value": "null",
        })

    return manifest


def corrupt_accuracy(rows, indices, rng):
    """Scenario 10: Quintile Q1 > Q5 inversions --> SLV-CSI-015."""
    manifest = []
    # Inject 60+ inversions -- target 65 to make sure threshold trips
    n_inversions = 65
    targets = rng.sample(range(len(rows)), min(n_inversions, len(rows)))
    for i in targets:
        old_q1 = rows[i].get("net_price_q1")
        old_q5 = rows[i].get("net_price_q5")
        # Force inversion: Q1 > Q5 by a large margin
        rows[i]["net_price_q1"] = 40000.0 + rng.uniform(0, 5000)
        rows[i]["net_price_q5"] = 10000.0 - rng.uniform(0, 2000)
        manifest.append({
            "row": i, "dimension": "accuracy",
            "field": "net_price_q1,net_price_q5",
            "strategy": "quintile_inversion",
            "target_rules": ["SLV-CSI-015"],
            "old_value": f"q1={old_q1},q5={old_q5}",
            "new_value": f"q1={rows[i]['net_price_q1']:.0f},q5={rows[i]['net_price_q5']:.0f}",
        })
    return manifest


def corrupt_reasonableness(rows, indices, rng):
    """Scenario 11: net_price outside [-5K, 80K] --> SLV-CSI-016.
    Scenario 12: cost_of_attendance outside [5K, 100K] --> SLV-CSI-017."""
    manifest = []
    targets = _pick_indices(rows, indices, rng, divisor=3)
    for i in targets:
        strategy = rng.choice([
            "np_extreme_high", "np_extreme_low",
            "coa_extreme_high", "coa_extreme_low",
        ])
        if strategy == "np_extreme_high":
            old = rows[i].get("net_price_annual")
            new = float(rng.randint(100_000, 500_000))
            rows[i]["net_price_annual"] = new
            rows[i]["net_price_4yr"] = new * 4
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "net_price_annual",
                "strategy": strategy,
                "target_rules": ["SLV-CSI-016"],
                "old_value": str(old), "new_value": str(new),
            })
        elif strategy == "np_extreme_low":
            old = rows[i].get("net_price_annual")
            new = float(rng.randint(-50_000, -6_000))
            rows[i]["net_price_annual"] = new
            rows[i]["net_price_4yr"] = new * 4
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "net_price_annual",
                "strategy": strategy,
                "target_rules": ["SLV-CSI-016"],
                "old_value": str(old), "new_value": str(new),
            })
        elif strategy == "coa_extreme_high":
            old = rows[i].get("cost_of_attendance_annual")
            new = float(rng.randint(150_000, 500_000))
            rows[i]["cost_of_attendance_annual"] = new
            rows[i]["cost_of_attendance_4yr"] = new * 4
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "cost_of_attendance_annual",
                "strategy": strategy,
                "target_rules": ["SLV-CSI-017"],
                "old_value": str(old), "new_value": str(new),
            })
        else:  # coa_extreme_low
            old = rows[i].get("cost_of_attendance_annual")
            new = float(rng.randint(100, 4_000))
            rows[i]["cost_of_attendance_annual"] = new
            rows[i]["cost_of_attendance_4yr"] = new * 4
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "cost_of_attendance_annual",
                "strategy": strategy,
                "target_rules": ["SLV-CSI-017"],
                "old_value": str(old), "new_value": str(new),
            })
    return manifest


def corrupt_volume(rows, indices, rng):
    """Scenario 13: Row-count manipulation --> SLV-CSI-001.

    SLV-CSI-001 name: 'Row count exact match to Bronze (3,039 +/- 5)'. Push
    outside the +/-5 window by appending duplicates with unique unitids.
    """
    manifest = []
    n_extras = 50  # Push from 3,039 to ~3,089 -- well outside +/-5
    source_rows = rng.sample(range(len(rows)), min(n_extras, len(rows)))
    for src in source_rows:
        dupe = copy.deepcopy(rows[src])
        dupe["unitid"] = rng.randint(900_000, 999_999)
        dupe["record_id"] = _compute_record_id(dupe["unitid"])
        dupe["institution_name"] = f"{dupe['institution_name']} [vol]"
        rows.append(dupe)
    manifest.append({
        "row": -1, "dimension": "volume", "field": "row_count",
        "strategy": "mass_inject_50",
        "target_rules": ["SLV-CSI-001"],
        "old_value": str(len(rows) - n_extras),
        "new_value": str(len(rows)),
    })
    return manifest


# ---------------------------------------------------------------------------
# Iceberg shadow table management
# ---------------------------------------------------------------------------

ICEBERG_SCHEMA_FIELDS = [
    ("record_id", pa.string()),
    ("unitid", pa.int64()),
    ("institution_name", pa.string()),
    ("state_abbr", pa.string()),
    ("institution_control", pa.string()),
    ("cost_of_attendance_annual", pa.float64()),
    ("cost_of_attendance_4yr", pa.float64()),
    ("net_price_annual", pa.float64()),
    ("net_price_4yr", pa.float64()),
    ("net_price_q1", pa.float64()),
    ("net_price_q2", pa.float64()),
    ("net_price_q3", pa.float64()),
    ("net_price_q4", pa.float64()),
    ("net_price_q5", pa.float64()),
    ("tuition_in_state", pa.float64()),
    ("tuition_out_of_state", pa.float64()),
    ("room_board_on_campus", pa.float64()),
    ("room_board_off_campus", pa.float64()),
    ("books_supplies", pa.float64()),
    ("costt4_a_raw", pa.float64()),
    ("costt4_p_raw", pa.float64()),
    ("npt4_pub_raw", pa.float64()),
    ("npt4_priv_raw", pa.float64()),
    ("npt41_pub_raw", pa.float64()),
    ("npt42_pub_raw", pa.float64()),
    ("npt43_pub_raw", pa.float64()),
    ("npt44_pub_raw", pa.float64()),
    ("npt45_pub_raw", pa.float64()),
    ("npt41_priv_raw", pa.float64()),
    ("npt42_priv_raw", pa.float64()),
    ("npt43_priv_raw", pa.float64()),
    ("npt44_priv_raw", pa.float64()),
    ("npt45_priv_raw", pa.float64()),
    ("source_load_date", pa.date32()),
    ("ingested_at", pa.timestamp("us")),
]


def rows_to_arrow(rows: list[dict]) -> pa.Table:
    arrays = {}
    for col_name, col_type in ICEBERG_SCHEMA_FIELDS:
        values = [r.get(col_name) for r in rows]
        try:
            arrays[col_name] = pa.array(values, type=col_type)
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            arrays[col_name] = pa.array(values)
    return pa.table(arrays)


def write_shadow_parquet(arrow_table: pa.Table, cycle_num: int) -> Path:
    data_dir = SHADOW_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_file = data_dir / f"chaos-cycle-{cycle_num}.parquet"
    pq.write_table(arrow_table, str(out_file))
    return out_file


def register_shadow_in_catalog(parquet_path: Path):
    """Register the shadow Silver table in the Iceberg catalog under
    shadow_base namespace (dq_runner maps base -> shadow_base when
    --shadow is passed)."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        DateType, DoubleType, LongType, NestedField, StringType, TimestampType,
    )

    catalog = get_catalog(SILVER_WAREHOUSE_PATH, CATALOG_PATH)

    try:
        catalog.create_namespace("shadow_base")
    except Exception:
        pass

    try:
        catalog.drop_table("shadow_base.college_scorecard_institution")
    except Exception:
        pass

    # Mirror the Silver schema field IDs (from college_scorecard_institution_transformer.get_silver_schema)
    iceberg_schema = Schema(
        NestedField(1, "record_id", StringType(), required=False),
        NestedField(2, "unitid", LongType(), required=False),
        NestedField(3, "institution_name", StringType(), required=False),
        NestedField(4, "state_abbr", StringType(), required=False),
        NestedField(5, "institution_control", StringType(), required=False),
        NestedField(6, "cost_of_attendance_annual", DoubleType(), required=False),
        NestedField(7, "cost_of_attendance_4yr", DoubleType(), required=False),
        NestedField(8, "net_price_annual", DoubleType(), required=False),
        NestedField(9, "net_price_4yr", DoubleType(), required=False),
        NestedField(10, "net_price_q1", DoubleType(), required=False),
        NestedField(11, "net_price_q2", DoubleType(), required=False),
        NestedField(12, "net_price_q3", DoubleType(), required=False),
        NestedField(13, "net_price_q4", DoubleType(), required=False),
        NestedField(14, "net_price_q5", DoubleType(), required=False),
        NestedField(15, "tuition_in_state", DoubleType(), required=False),
        NestedField(16, "tuition_out_of_state", DoubleType(), required=False),
        NestedField(17, "room_board_on_campus", DoubleType(), required=False),
        NestedField(18, "room_board_off_campus", DoubleType(), required=False),
        NestedField(19, "books_supplies", DoubleType(), required=False),
        NestedField(20, "costt4_a_raw", DoubleType(), required=False),
        NestedField(21, "costt4_p_raw", DoubleType(), required=False),
        NestedField(22, "npt4_pub_raw", DoubleType(), required=False),
        NestedField(23, "npt4_priv_raw", DoubleType(), required=False),
        NestedField(24, "npt41_pub_raw", DoubleType(), required=False),
        NestedField(25, "npt42_pub_raw", DoubleType(), required=False),
        NestedField(26, "npt43_pub_raw", DoubleType(), required=False),
        NestedField(27, "npt44_pub_raw", DoubleType(), required=False),
        NestedField(28, "npt45_pub_raw", DoubleType(), required=False),
        NestedField(29, "npt41_priv_raw", DoubleType(), required=False),
        NestedField(30, "npt42_priv_raw", DoubleType(), required=False),
        NestedField(31, "npt43_priv_raw", DoubleType(), required=False),
        NestedField(32, "npt44_priv_raw", DoubleType(), required=False),
        NestedField(33, "npt45_priv_raw", DoubleType(), required=False),
        NestedField(34, "source_load_date", DateType(), required=False),
        NestedField(35, "ingested_at", TimestampType(), required=False),
    )

    shadow_table = catalog.create_table(
        "shadow_base.college_scorecard_institution", schema=iceberg_schema
    )
    data = pq.read_table(str(parquet_path))
    shadow_table.append(data)
    return shadow_table


def run_dq_rules_shadow():
    """Invoke the shared DQ runner against shadow_base for this spec.

    Uses a silver-warehouse-backed catalog so the runner can resolve
    shadow_base.college_scorecard_institution. Also temporarily promotes
    any 'proposed' rules in this spec to 'active' status in memory so the
    chaos run exercises the full rule set (the spec is pre-approval).
    """
    import brightsmith.config as bs_config
    from brightsmith.infra import dq_runner as dq_mod
    from brightsmith.infra.iceberg_setup import get_catalog

    bs_config.WAREHOUSE_PATH = SILVER_WAREHOUSE_PATH

    # Monkey-patch load_rules so proposed rules execute in the chaos harness
    original_load_rules = dq_mod.load_rules

    def load_rules_with_proposed(spec=None):
        rules = original_load_rules(spec=spec)
        for r in rules:
            if r.get("spec") == "silver-base-college-scorecard-institution":
                # Elevate proposed rules so run_rules does not filter them out
                if r.get("status", "").lower() == "proposed":
                    r["status"] = "active"
        return rules

    dq_mod.load_rules = load_rules_with_proposed
    try:
        catalog = get_catalog(SILVER_WAREHOUSE_PATH, CATALOG_PATH)
        result = dq_mod.run_rules(
            spec="silver-base-college-scorecard-institution",
            shadow=True,
            catalog=catalog,
        )
    finally:
        dq_mod.load_rules = original_load_rules
    return result


def cleanup_shadow():
    """Drop the shadow table and remove parquet files."""
    try:
        from brightsmith.infra.iceberg_setup import get_catalog
        catalog = get_catalog(SILVER_WAREHOUSE_PATH, CATALOG_PATH)
        try:
            catalog.drop_table("shadow_base.college_scorecard_institution")
        except Exception:
            pass
    except Exception:
        pass
    if SHADOW_DIR.exists():
        shutil.rmtree(SHADOW_DIR)


# ---------------------------------------------------------------------------
# Cycle orchestration
# ---------------------------------------------------------------------------

CORRUPTION_FUNCTIONS = [
    corrupt_uniqueness,
    corrupt_validity,
    corrupt_completeness,
    corrupt_consistency,
    corrupt_coverage,
    corrupt_accuracy,
    corrupt_reasonableness,
    corrupt_volume,
]


def run_cycle(cycle_num: int, rate: float, seed: int) -> dict:
    print(f"\n{'='*72}")
    print(f"SILVER CYCLE {cycle_num} | Rate: {rate*100:.0f}% | Seed: {seed}")
    print(f"{'='*72}")

    rng = random.Random(seed)

    print("Generating clean Silver-shaped baseline...")
    rows = generate_clean_silver_data(rng)
    original_count = len(rows)
    print(f"  Baseline row count: {original_count}")
    ctrl_counts = {"Public": 0, "Private nonprofit": 0, "Private for-profit": 0}
    for r in rows:
        ctrl_counts[r["institution_control"]] = ctrl_counts.get(r["institution_control"], 0) + 1
    print(f"  Control mix: {ctrl_counts}")

    n_corrupt = int(original_count * rate)
    per_function = max(1, n_corrupt // len(CORRUPTION_FUNCTIONS))
    all_indices = list(range(original_count))

    all_manifest = []
    for func in CORRUPTION_FUNCTIONS:
        indices = rng.sample(all_indices, min(per_function, len(all_indices)))
        try:
            entries = func(rows, indices, rng)
            all_manifest.extend(entries)
            dim = func.__name__.replace("corrupt_", "")
            print(f"  {dim}: {len(entries)} corruptions")
        except Exception as e:
            print(f"  ERROR in {func.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print(f"  Total corruptions: {len(all_manifest)}")
    print(f"  Final row count: {len(rows)} (was {original_count})")

    dq_result = {
        "run_id": "error", "rules_total": 0, "rules_passed": 0,
        "rules_failed": 0, "rules_errored": 0, "p0_passed": True, "results": [],
    }
    try:
        arrow_table = rows_to_arrow(rows)
        parquet_path = write_shadow_parquet(arrow_table, cycle_num)
        print(f"  Parquet: {parquet_path}")

        register_shadow_in_catalog(parquet_path)
        print("  Registered shadow_base.college_scorecard_institution")

        print("Running DQ rules with --shadow...")
        dq_result = run_dq_rules_shadow()
        print(
            f"  Run ID: {dq_result.get('run_id')} | "
            f"Total: {dq_result.get('rules_total')} | "
            f"Passed: {dq_result.get('rules_passed')} | "
            f"Failed: {dq_result.get('rules_failed')} | "
            f"Errored: {dq_result.get('rules_errored', 0)}"
        )
        print(f"  P0 gate: {'PASS' if dq_result.get('p0_passed') else 'FAIL'}")

        print("\n  Per-rule outcomes:")
        for r in dq_result.get("results", []):
            if r.get("error"):
                status = "ERROR"
            elif r["passed"]:
                status = "PASS (silent)"
            else:
                status = "FAIL (fired)"
            print(f"    {r['rule_id']:<16} {status:<14} value={r.get('raw_value', '?')}")
    except Exception as e:
        print(f"  ERROR during shadow creation/DQ run: {e}")
        import traceback
        traceback.print_exc()

    return {
        "cycle": cycle_num,
        "rate": rate,
        "seed": seed,
        "original_row_count": original_count,
        "corrupted_row_count": len(rows),
        "total_corruptions": len(all_manifest),
        "manifest": all_manifest,
        "dq_result": dq_result,
    }


def analyze_gaps(cycle_result: dict) -> dict:
    dq_result = cycle_result["dq_result"]
    manifest = cycle_result["manifest"]

    failed_rules = [r for r in dq_result.get("results", [])
                    if not r["passed"] and not r.get("error")]
    passed_rules = [r for r in dq_result.get("results", []) if r["passed"]]
    errored_rules = [r for r in dq_result.get("results", []) if r.get("error")]

    # Collect target rules mentioned in manifest
    expected_fires: dict[str, list[str]] = {}
    for entry in manifest:
        for rule_id in entry.get("target_rules", []):
            expected_fires.setdefault(rule_id, []).append(entry["strategy"])

    actually_fired = {r["rule_id"] for r in failed_rules}
    expected_set = set(expected_fires.keys())

    return {
        "failed_rules": [{"rule_id": r["rule_id"], "raw_value": r.get("raw_value")}
                         for r in failed_rules],
        "passed_rules": [{"rule_id": r["rule_id"], "raw_value": r.get("raw_value")}
                         for r in passed_rules],
        "errored_rules": [{"rule_id": r["rule_id"], "error": r.get("error")}
                          for r in errored_rules],
        "rules_fired": sorted(actually_fired),
        "rules_silent": sorted({r["rule_id"] for r in passed_rules}),
        "rules_errored": sorted({r["rule_id"] for r in errored_rules}),
        "expected_to_fire": sorted(expected_set),
        "expected_and_fired": sorted(expected_set & actually_fired),
        "expected_but_silent": sorted(expected_set - actually_fired),
        "unexpected_fires": sorted(actually_fired - expected_set),
        "total_rules": len(dq_result.get("results", [])),
        "detection_rate": round(
            len(expected_set & actually_fired) / max(len(expected_set), 1), 3
        ),
    }


def main() -> dict:
    all_cycles = []
    previous_fired: set[str] = set()
    consecutive_stable = 0

    for cycle_num, rate in enumerate(RATES, 1):
        cleanup_shadow()
        seed = SEED_BASE + cycle_num
        cycle_result = run_cycle(cycle_num, rate, seed)
        gap = analyze_gaps(cycle_result)

        current_fired = set(gap["rules_fired"])
        if cycle_num > 1 and current_fired == previous_fired:
            consecutive_stable += 1
        else:
            consecutive_stable = 0
        previous_fired = current_fired

        all_cycles.append({
            "cycle": cycle_num,
            "rate": rate,
            "seed": seed,
            "corruptions": cycle_result["total_corruptions"],
            "row_count": cycle_result["corrupted_row_count"],
            "dq_total": cycle_result["dq_result"].get("rules_total"),
            "dq_passed": cycle_result["dq_result"].get("rules_passed"),
            "dq_failed": cycle_result["dq_result"].get("rules_failed"),
            "dq_errored": cycle_result["dq_result"].get("rules_errored", 0),
            "gap_analysis": gap,
            "manifest_entries": cycle_result["manifest"],
        })

        print("\n  Gap Analysis:")
        print(f"    Expected to fire:   {gap['expected_to_fire']}")
        print(f"    Actually fired:     {gap['rules_fired']}")
        print(f"    Expected & fired:   {gap['expected_and_fired']}")
        print(f"    Expected but silent:{gap['expected_but_silent']}")
        print(f"    Unexpected fires:   {gap['unexpected_fires']}")
        print(f"    Detection rate:     {gap['detection_rate']*100:.1f}%")

        if consecutive_stable >= 2:
            print(f"\n  Stability: same rules fired 2+ cycles in a row.")

    cleanup_shadow()

    manifest_data = {
        "spec": "silver-base-college-scorecard-institution",
        "table": "base.college_scorecard_institution",
        "shadow_table": "shadow_base.college_scorecard_institution",
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest_data, indent=2, default=str) + "\n")
    print(f"\nManifest: {MANIFEST_PATH}")

    return manifest_data


if __name__ == "__main__":
    result = main()
    print(f"\n{'='*72}")
    print("SUMMARY")
    print(f"{'='*72}")
    for c in result["cycles"]:
        ga = c["gap_analysis"]
        print(
            f"Cycle {c['cycle']} ({c['rate']*100:.0f}%): "
            f"fired={len(ga['rules_fired'])}/{c['dq_total']}, "
            f"expected_silent={ga['expected_but_silent']}"
        )
