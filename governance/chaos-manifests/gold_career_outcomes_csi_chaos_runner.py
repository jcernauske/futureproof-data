"""
Chaos Monkey CSI Adversarial Hardening Runner
Spec:  gold-career-outcomes-college-scorecard (CSI enrichment, Zone 3)
Rules under test: GLD-CSI-001 through GLD-CSI-009 (9 rules)
Table: consumable.career_outcomes (real Iceberg, 69,947 rows)

Pattern: shadow corruption in DuckDB in-memory. The production Iceberg table
is never mutated. We:
    1. Load the real snapshot into DuckDB memory via a temp parquet
    2. Clone the 69,947-row baseline to a per-cycle shadow
    3. Apply an 8-scenario corruption plan (one scenario per CSI rule 002-009;
       row-count scenario covers CSI-001)
    4. Execute each of the 9 GLD-CSI-* rule SQLs against the shadow table
    5. Record PASS / FAIL (fail = rule fires, i.e. detection) per scenario
    6. Tally detection rate per cycle

Run: uv run python governance/chaos-manifests/gold_career_outcomes_csi_chaos_runner.py
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pyarrow.parquet as pq
from pyiceberg.catalog import load_catalog

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
CATALOG_DB = PROJECT_ROOT / "data/catalog/catalog.db"
GOLD_WAREHOUSE = PROJECT_ROOT / "data/gold/iceberg_warehouse"
SNAPSHOT_PARQUET = Path("/tmp/career_outcomes_real_csi_chaos.parquet")

RULES_FILE = PROJECT_ROOT / "governance/dq-rules/gold-career-outcomes-college-scorecard.json"

# Cycles: 5 requested; escalate seed per cycle to vary sampling
N_CYCLES = 5
SEED_BASE = 42


# ---------------------------------------------------------------------------
# Load real snapshot
# ---------------------------------------------------------------------------

def load_real_snapshot() -> int:
    cat = load_catalog(
        "brightsmith",
        **{
            "type": "sql",
            "uri": f"sqlite:///{CATALOG_DB}",
            "warehouse": f"file://{GOLD_WAREHOUSE}",
        },
    )
    tbl = cat.load_table("consumable.career_outcomes")
    arrow = tbl.scan().to_arrow()
    pq.write_table(arrow, str(SNAPSHOT_PARQUET))
    return arrow.num_rows


# ---------------------------------------------------------------------------
# Load the 9 GLD-CSI-* rule SQLs
# ---------------------------------------------------------------------------

def load_csi_rules() -> list[dict]:
    rules = json.loads(RULES_FILE.read_text())["rules"]
    csi = [r for r in rules if r["rule_id"].startswith("GLD-CSI-")]
    csi.sort(key=lambda r: r["rule_id"])
    return csi


def rewrite_sql_for_shadow(sql: str, shadow_table: str) -> str:
    """Replace the production qualified name with the shadow name for in-memory exec."""
    return sql.replace("consumable.career_outcomes", shadow_table)


def execute_rule(con: duckdb.DuckDBPyConnection, rule: dict, shadow_table: str) -> dict:
    """Run one rule's SQL against the shadow table and classify violation per threshold.
    Returns {'fired': bool, 'value': <scalar>, 'kind': 'count'|'scalar'|'rowset'}.
    """
    sql = rewrite_sql_for_shadow(rule["sql"], shadow_table)
    threshold = rule["threshold"]
    res = con.execute(sql).fetchall()

    # DQ runner semantics: rules return either
    #  (a) a single scalar violation count/flag -> compare to threshold 'result = 0' or 'result <= X'
    #  (b) a rowset of offending rows -> 'result_count = 0'
    if threshold.startswith("result_count"):
        # rowset mode
        fired = len(res) > 0
        return {"fired": fired, "value": len(res), "kind": "rowset"}
    # scalar mode: one row, one column
    val = res[0][0] if res and res[0] else 0
    # parse threshold like 'result = 0' or 'result <= 100.0'
    fired = False
    if "=" in threshold and "<=" not in threshold and ">=" not in threshold:
        target = float(threshold.split("=")[-1].strip())
        fired = float(val) != target
    elif "<=" in threshold:
        target = float(threshold.split("<=")[-1].strip())
        fired = float(val) > target
    elif ">=" in threshold:
        target = float(threshold.split(">=")[-1].strip())
        fired = float(val) < target
    return {"fired": fired, "value": val, "kind": "scalar"}


# ---------------------------------------------------------------------------
# Corruption scenarios — one per rule (001-009)
# ---------------------------------------------------------------------------

def scenario_001_drop_rows(con: duckdb.DuckDBPyConnection, shadow: str, rng: random.Random) -> dict:
    # Drop exactly 100 rows -> row count 69,847 != 69,947
    # Select a deterministic per-cycle subset via ORDER BY + LIMIT with seed.
    seed = rng.random()
    con.execute(f"SET threads TO 1")
    con.execute(
        f"""
        DELETE FROM {shadow} WHERE record_id IN (
            SELECT record_id FROM {shadow}
            ORDER BY hash(record_id || '{seed}'::VARCHAR)
            LIMIT 100
        )
        """
    )
    return {"dropped": 100}


def scenario_002_netprice_gt_coa(con: duckdb.DuckDBPyConnection, shadow: str, rng: random.Random) -> dict:
    # Flip sign / inflate net_price_annual on 50 rows so NP > COA.
    # Pick 50 rows where both fields are non-null and NP < COA currently.
    seed = rng.random()
    con.execute(
        f"""
        UPDATE {shadow}
        SET net_price_annual = cost_of_attendance_annual * 1.5
        WHERE record_id IN (
            SELECT record_id FROM {shadow}
            WHERE net_price_annual IS NOT NULL
              AND cost_of_attendance_annual IS NOT NULL
              AND net_price_annual <= cost_of_attendance_annual
            ORDER BY hash(record_id || '{seed}'::VARCHAR)
            LIMIT 50
        )
        """
    )
    return {"inflated": 50}


def scenario_003_netprice4yr_mismatch(con: duckdb.DuckDBPyConnection, shadow: str, rng: random.Random) -> dict:
    # Corrupt net_price_4yr to 2x annual on 30 rows.
    seed = rng.random()
    con.execute(
        f"""
        UPDATE {shadow}
        SET net_price_4yr = net_price_annual * 2
        WHERE record_id IN (
            SELECT record_id FROM {shadow}
            WHERE net_price_annual IS NOT NULL
              AND net_price_4yr IS NOT NULL
            ORDER BY hash(record_id || '{seed}'::VARCHAR)
            LIMIT 30
        )
        """
    )
    return {"miscomputed": 30}


def scenario_004_netprice_below_floor(con: duckdb.DuckDBPyConnection, shadow: str, rng: random.Random) -> dict:
    # Set net_price_annual to -$50,000 on 10 rows (violates -$10k floor).
    seed = rng.random()
    con.execute(
        f"""
        UPDATE {shadow}
        SET net_price_annual = -50000.0
        WHERE record_id IN (
            SELECT record_id FROM {shadow}
            WHERE net_price_annual IS NOT NULL
            ORDER BY hash(record_id || '{seed}'::VARCHAR)
            LIMIT 10
        )
        """
    )
    return {"sub_floor": 10}


def scenario_005_null_netprice(con: duckdb.DuckDBPyConnection, shadow: str, rng: random.Random) -> dict:
    # Null out net_price_annual on 10% of rows -> pushes coverage below 90%.
    # Baseline coverage is ~95.45%. 10% null of total = 6,995 more nulls, new coverage ~85%.
    seed = rng.random()
    # Nulling 15% of currently-populated rows to guarantee drop below 90% across all cycles
    con.execute(
        f"""
        UPDATE {shadow}
        SET net_price_annual = NULL
        WHERE record_id IN (
            SELECT record_id FROM {shadow}
            WHERE net_price_annual IS NOT NULL
            ORDER BY hash(record_id || '{seed}'::VARCHAR)
            LIMIT (SELECT CAST(COUNT(*) * 0.10 AS BIGINT) FROM {shadow})
        )
        """
    )
    return {"nulled_pct_of_total": 10}


def scenario_006_null_coa(con: duckdb.DuckDBPyConnection, shadow: str, rng: random.Random) -> dict:
    # Null 10% of COA to bring coverage below 90%
    seed = rng.random()
    con.execute(
        f"""
        UPDATE {shadow}
        SET cost_of_attendance_annual = NULL
        WHERE record_id IN (
            SELECT record_id FROM {shadow}
            WHERE cost_of_attendance_annual IS NOT NULL
            ORDER BY hash(record_id || '{seed}'::VARCHAR)
            LIMIT (SELECT CAST(COUNT(*) * 0.10 AS BIGINT) FROM {shadow})
        )
        """
    )
    return {"nulled_pct_of_total": 10}


def scenario_007_null_instctrl(con: duckdb.DuckDBPyConnection, shadow: str, rng: random.Random) -> dict:
    # Null 10% of institution_control to bring coverage below 95% (97.42% -> ~87%)
    seed = rng.random()
    con.execute(
        f"""
        UPDATE {shadow}
        SET institution_control = NULL
        WHERE record_id IN (
            SELECT record_id FROM {shadow}
            WHERE institution_control IS NOT NULL
            ORDER BY hash(record_id || '{seed}'::VARCHAR)
            LIMIT (SELECT CAST(COUNT(*) * 0.10 AS BIGINT) FROM {shadow})
        )
        """
    )
    return {"nulled_pct_of_total": 10}


def scenario_008_phantom_unmatched(con: duckdb.DuckDBPyConnection, shadow: str, rng: random.Random) -> dict:
    # Fabricate 500 "phantom unmatched" distinct UNITIDs: null all 3 CSI-enriched
    # attributes on rows where the UNITID currently IS matched.
    # We pick 500 distinct matched UNITIDs and null their institution_control,
    # net_price_annual, cost_of_attendance_annual across ALL rows for those UNITIDs.
    seed = rng.random()
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _phantom_unitids AS
        SELECT DISTINCT unitid FROM {shadow}
        WHERE institution_control IS NOT NULL
          AND net_price_annual IS NOT NULL
          AND cost_of_attendance_annual IS NOT NULL
        ORDER BY hash(unitid::VARCHAR || '{seed}'::VARCHAR)
        LIMIT 500
        """
    )
    n = con.execute("SELECT COUNT(*) FROM _phantom_unitids").fetchone()[0]
    con.execute(
        f"""
        UPDATE {shadow}
        SET institution_control = NULL,
            net_price_annual = NULL,
            cost_of_attendance_annual = NULL,
            net_price_4yr = NULL,
            tuition_in_state = NULL,
            tuition_out_of_state = NULL,
            room_board_on_campus = NULL
        WHERE unitid IN (SELECT unitid FROM _phantom_unitids)
        """
    )
    return {"phantom_unitids": n}


def scenario_009_bad_instctrl_value(con: duckdb.DuckDBPyConnection, shadow: str, rng: random.Random) -> dict:
    # Insert 'Unknown' (out-of-set value) for institution_control on 25 rows.
    seed = rng.random()
    con.execute(
        f"""
        UPDATE {shadow}
        SET institution_control = 'Unknown'
        WHERE record_id IN (
            SELECT record_id FROM {shadow}
            WHERE institution_control IS NOT NULL
            ORDER BY hash(record_id || '{seed}'::VARCHAR)
            LIMIT 25
        )
        """
    )
    return {"out_of_set": 25}


SCENARIO_PLAN = [
    ("GLD-CSI-001", "drop_100_rows", scenario_001_drop_rows),
    ("GLD-CSI-002", "netprice_gt_coa_50rows", scenario_002_netprice_gt_coa),
    ("GLD-CSI-003", "netprice4yr_mismatch_30rows", scenario_003_netprice4yr_mismatch),
    ("GLD-CSI-004", "netprice_below_floor_10rows", scenario_004_netprice_below_floor),
    ("GLD-CSI-005", "null_netprice_10pct", scenario_005_null_netprice),
    ("GLD-CSI-006", "null_coa_10pct", scenario_006_null_coa),
    ("GLD-CSI-007", "null_instctrl_10pct", scenario_007_null_instctrl),
    ("GLD-CSI-008", "phantom_500_unmatched_unitids", scenario_008_phantom_unmatched),
    ("GLD-CSI-009", "bad_instctrl_value_25rows", scenario_009_bad_instctrl_value),
]


# ---------------------------------------------------------------------------
# Cycle executor: each scenario is tested in ISOLATION against a fresh shadow.
# Isolation is the right pattern here because we want to attribute each rule's
# firing to exactly one scenario (not to cross-talk from other scenarios).
# ---------------------------------------------------------------------------

def run_cycle(cycle_idx: int, rules: list[dict]) -> dict:
    seed = SEED_BASE + cycle_idx
    rng = random.Random(seed)
    con = duckdb.connect(":memory:")

    # Load real baseline once per cycle
    con.execute(
        f"CREATE TABLE baseline AS SELECT * FROM read_parquet('{SNAPSHOT_PARQUET}')"
    )
    baseline_rows = con.execute("SELECT COUNT(*) FROM baseline").fetchone()[0]

    scenario_results = []
    for rule_id, scenario_name, fn in SCENARIO_PLAN:
        shadow = f"shadow_{rule_id.replace('-', '_').lower()}"
        con.execute(f"CREATE OR REPLACE TABLE {shadow} AS SELECT * FROM baseline")
        effect = fn(con, shadow, rng)

        # Execute ALL 9 rules against this shadow
        rule_firings = {}
        for r in rules:
            try:
                result = execute_rule(con, r, shadow)
                rule_firings[r["rule_id"]] = result
            except Exception as e:
                rule_firings[r["rule_id"]] = {"fired": False, "error": str(e)}

        target_fired = rule_firings.get(rule_id, {}).get("fired", False)
        scenario_results.append({
            "rule_id": rule_id,
            "scenario": scenario_name,
            "effect": effect,
            "target_rule_detected": target_fired,
            "target_rule_value": rule_firings.get(rule_id, {}).get("value"),
            "collateral_firings": [
                rid for rid, r in rule_firings.items()
                if r.get("fired") and rid != rule_id
            ],
        })

    con.close()
    detected = sum(1 for s in scenario_results if s["target_rule_detected"])
    return {
        "cycle": cycle_idx,
        "seed": seed,
        "baseline_rows": baseline_rows,
        "scenarios": scenario_results,
        "detection_count": detected,
        "scenarios_total": len(scenario_results),
        "detection_rate_pct": round(100.0 * detected / len(scenario_results), 2),
    }


def main() -> int:
    print(f"[chaos-csi] Loading real Iceberg snapshot ...")
    n = load_real_snapshot()
    print(f"[chaos-csi] Baseline: {n} rows")
    if n != 69947:
        print(f"[chaos-csi] WARNING: baseline row count {n} != 69947; proceeding.")

    rules = load_csi_rules()
    print(f"[chaos-csi] Loaded {len(rules)} GLD-CSI-* rules: "
          f"{[r['rule_id'] for r in rules]}")

    all_cycles = []
    for c in range(1, N_CYCLES + 1):
        print(f"[chaos-csi] --- Cycle {c}/{N_CYCLES} ---")
        cyc = run_cycle(c, rules)
        print(f"[chaos-csi] Cycle {c}: detection {cyc['detection_count']}/"
              f"{cyc['scenarios_total']} ({cyc['detection_rate_pct']}%)")
        all_cycles.append(cyc)

    overall = {
        "spec": "gold-career-outcomes-college-scorecard",
        "rules_tested": [r["rule_id"] for r in rules],
        "cycles": all_cycles,
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    out_json = PROJECT_ROOT / "governance/chaos-manifests/gold-career-outcomes-csi-manifest.json"
    out_json.write_text(json.dumps(overall, indent=2, default=str))
    print(f"[chaos-csi] Wrote manifest: {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
