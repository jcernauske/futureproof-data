"""Per-scenario isolated probes for silver-base-bea-rpp.

Runs each scenario from silver_bea_rpp_chaos_runner.py against a CLEAN
shadow copy of base.bea_rpp and records the set of fired rule ids per
scenario.  Produces an unambiguous per-scenario -> rule-id matrix that
the chaos report can use for attribution.
"""
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from silver_bea_rpp_chaos_runner import (  # noqa: E402
    CYCLE_SCENARIOS,
    PROJECT_ROOT,
    SHADOW_FQN,
    SPEC_NAME,
    cleanup_shadow,
    load_source_rows,
    register_shadow,
    rows_to_arrow,
    run_dq_rules_shadow,
    safety_check,
    write_shadow_parquet,
)


# Build the flat (scenario_fn, label) list from every cycle, preserving
# order and deduping.
def _collect_scenarios():
    seen = set()
    plan = []
    for cycle_num in sorted(CYCLE_SCENARIOS.keys()):
        for fn in CYCLE_SCENARIOS[cycle_num]["scenarios"]:
            if fn.__name__ in seen:
                continue
            seen.add(fn.__name__)
            plan.append(fn)
    return plan


def run_probe(cycle_num, fn):
    print("\n" + "-" * 72)
    print(f"PROBE {cycle_num}: {fn.__name__}")
    print("-" * 72)
    rows, schema = load_source_rows()
    original_count = len(rows)
    entries = fn(rows)
    print(f"  manifest entries: {len(entries)}")
    print(f"  row count: {original_count} -> {len(rows)}")

    arrow_table = rows_to_arrow(rows, schema)
    parquet_path = write_shadow_parquet(arrow_table, cycle_num)
    register_shadow(parquet_path)

    dq_result = run_dq_rules_shadow()
    results = dq_result.get("results", [])
    failed = [r for r in results if not r.get("passed") and not r.get("error")]
    errored = [r for r in results if r.get("error")]

    fired_ids = sorted(r.get("rule_id") for r in failed)
    errored_ids = sorted(r.get("rule_id") for r in errored)

    print(f"  fired: {fired_ids}")
    if errored_ids:
        print(f"  errored: {errored_ids}")

    cleanup_shadow()
    return {
        "probe": cycle_num,
        "scenario": fn.__name__,
        "manifest": entries,
        "original_count": original_count,
        "corrupted_count": len(rows),
        "fired_rule_ids": fired_ids,
        "errored_rule_ids": errored_ids,
        "rules_total": len(results),
    }


def main():
    safety_check()
    plan = _collect_scenarios()
    print(f"Running {len(plan)} isolated probes...")

    probe_results = []
    for i, fn in enumerate(plan, start=100):
        try:
            probe_results.append(run_probe(i, fn))
        except Exception as exc:
            print(f"  ERROR in {fn.__name__}: {exc}")
            import traceback
            traceback.print_exc()
            probe_results.append({
                "probe": i,
                "scenario": fn.__name__,
                "error": str(exc),
            })
        finally:
            cleanup_shadow()

    out = {
        "spec": SPEC_NAME,
        "shadow_table": SHADOW_FQN,
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "probes": probe_results,
    }
    out_path = (
        PROJECT_ROOT
        / "governance/chaos-manifests/silver-base-bea-rpp-probes.json"
    )
    out_path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\nProbe matrix written: {out_path}")

    print("\n" + "=" * 72)
    print("PROBE SUMMARY")
    print("=" * 72)
    print(f"{'#':>3}  {'scenario':<44}  {'fired':<6}  rule ids")
    for p in probe_results:
        if "error" in p:
            print(f"{p['probe']:>3}  {p['scenario']:<44}  ERROR  {p['error']}")
            continue
        print(
            f"{p['probe']:>3}  {p['scenario']:<44}  "
            f"{len(p['fired_rule_ids']):<6}  "
            f"{', '.join(p['fired_rule_ids']) or '(none)'}"
        )


if __name__ == "__main__":
    main()
