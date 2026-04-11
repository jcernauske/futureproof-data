"""Extra targeted probes for silver-base-bea-rpp.

These test additional corner cases that the main probe set did NOT
isolate cleanly:

  E1. Self-consistent divergence from Bronze — set CA rpp_all_items=105.0
      AND purchasing_power_multiplier=100.0/105.0 so the inverse invariant
      (SIL-BEA-021) passes.  Only a dedicated Silver<->Bronze referential
      integrity rule can catch this.
  E2. Missing all 4 census regions in a different way — relabel
      every Northeast row as 'Midwest' (9 rows) so Northeast becomes
      invisible.  Tests coverage on a different region.
  E3. DC state_abbr flipped to a non-existent code 'ZZ' — exercises the
      canonical-set rule vs a pure regex rule.
  E4. data_year set to 2025 (future) — tests the literal vs range check
      on data_year (literal=2024 should fire).
  E5. purchasing_power_multiplier set to None on an estimate row — pure
      completeness probe.
  E6. state_fips set to '99' (unknown) on Alaska row — FIPS canonical set.
  E7. Duplicate state_fips WITHOUT changing record_id — tests state_fips
      uniqueness independently from record_id uniqueness.
  E8. Set all 51 verification_status to 'bea_official' — count rule = 51.
"""
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import copy  # noqa: E402
from silver_bea_rpp_chaos_runner import (  # noqa: E402
    PROJECT_ROOT,
    SHADOW_FQN,
    SPEC_NAME,
    _find_idx,
    cleanup_shadow,
    load_source_rows,
    register_shadow,
    rows_to_arrow,
    run_dq_rules_shadow,
    safety_check,
    write_shadow_parquet,
)


def probe_self_consistent_divergence(rows):
    """E1: CA rpp=105.0, ppm=100/105 — inverse invariant stays satisfied."""
    idx = _find_idx(rows, "06")
    if idx is None:
        return []
    old_rpp = rows[idx]["rpp_all_items"]
    old_ppm = rows[idx]["purchasing_power_multiplier"]
    rows[idx]["rpp_all_items"] = 105.0
    rows[idx]["purchasing_power_multiplier"] = 100.0 / 105.0
    return [{
        "scenario": "E1_self_consistent_divergence_from_bronze",
        "dimensions": ["referential_integrity", "accuracy"],
        "field": "rpp_all_items + purchasing_power_multiplier",
        "strategy": "change_both_so_inverse_still_holds",
        "old_value": f"rpp={old_rpp}, ppm={old_ppm}",
        "new_value": "rpp=105.0, ppm=0.9524 (self-consistent, diverges from bronze=110.7)",
    }]


def probe_drop_northeast_region(rows):
    """E2: relabel all Northeast rows as Midwest."""
    count = 0
    for r in rows:
        if r.get("census_region") == "Northeast":
            r["census_region"] = "Midwest"
            count += 1
    return [{
        "scenario": "E2_drop_northeast_region",
        "dimensions": ["coverage"],
        "field": "census_region",
        "strategy": "relabel_all_northeast_as_midwest",
        "old_value": "9 Northeast rows",
        "new_value": f"{count} relabeled to Midwest",
    }]


def probe_dc_abbr_zz(rows):
    """E3: DC state_abbr='ZZ' — regex passes but canonical-set should fire."""
    idx = _find_idx(rows, "11")
    if idx is None:
        return []
    old = rows[idx]["state_abbr"]
    rows[idx]["state_abbr"] = "ZZ"
    return [{
        "scenario": "E3_dc_abbr_zz",
        "dimensions": ["validity", "accuracy"],
        "field": "state_abbr",
        "strategy": "set_regex_compliant_but_non_canonical",
        "old_value": str(old),
        "new_value": "ZZ",
    }]


def probe_data_year_future(rows):
    """E4: data_year=2025 on Alabama (01)."""
    idx = _find_idx(rows, "01")
    if idx is None:
        return []
    old = rows[idx]["data_year"]
    rows[idx]["data_year"] = 2025
    return [{
        "scenario": "E4_data_year_future",
        "dimensions": ["freshness", "validity"],
        "field": "data_year",
        "strategy": "set_future_year",
        "old_value": str(old),
        "new_value": "2025",
    }]


def probe_null_ppm(rows):
    """E5: null purchasing_power_multiplier on an estimate row."""
    idx = _find_idx(rows, "01")  # Alabama, estimate
    if idx is None:
        return []
    old = rows[idx]["purchasing_power_multiplier"]
    rows[idx]["purchasing_power_multiplier"] = None
    return [{
        "scenario": "E5_null_ppm",
        "dimensions": ["completeness"],
        "field": "purchasing_power_multiplier",
        "strategy": "null_out",
        "old_value": str(old),
        "new_value": "null",
    }]


def probe_state_fips_unknown(rows):
    """E6: state_fips='99' on Alaska — canonical-set FIPS check."""
    idx = _find_idx(rows, "02")
    if idx is None:
        return []
    rows[idx]["state_fips"] = "99"
    return [{
        "scenario": "E6_state_fips_unknown",
        "dimensions": ["validity"],
        "field": "state_fips",
        "strategy": "set_non_canonical_code",
        "old_value": "02",
        "new_value": "99",
    }]


def probe_duplicate_state_fips(rows):
    """E7: append a second row for Oregon with a unique record_id."""
    idx = _find_idx(rows, "41")  # Oregon
    if idx is None:
        return []
    dup = copy.deepcopy(rows[idx])
    dup["record_id"] = "rpp-oregon-duplicate-deadbeef"  # unique
    dup["state_name"] = "Oregon (shadow duplicate)"
    rows.append(dup)
    return [{
        "scenario": "E7_duplicate_state_fips",
        "dimensions": ["uniqueness"],
        "field": "state_fips",
        "strategy": "append_second_row_same_fips_unique_record_id",
        "old_value": "state_fips=41 appears 1x",
        "new_value": "state_fips=41 appears 2x (row count 52)",
    }]


def probe_all_bea_official(rows):
    """E8: mark every row as bea_official — count rule should fire hard."""
    for r in rows:
        r["verification_status"] = "bea_official"
    return [{
        "scenario": "E8_all_bea_official",
        "dimensions": ["accuracy", "consistency"],
        "field": "verification_status",
        "strategy": "mark_all_51_as_bea_official",
        "old_value": "8 bea_official, 43 estimate",
        "new_value": "51 bea_official, 0 estimate",
    }]


EXTRA_PROBES = [
    probe_self_consistent_divergence,
    probe_drop_northeast_region,
    probe_dc_abbr_zz,
    probe_data_year_future,
    probe_null_ppm,
    probe_state_fips_unknown,
    probe_duplicate_state_fips,
    probe_all_bea_official,
]


def run_probe(cycle_num, fn):
    print("\n" + "-" * 72)
    print(f"EXTRA PROBE {cycle_num}: {fn.__name__}")
    print("-" * 72)
    rows, schema = load_source_rows()
    original_count = len(rows)
    entries = fn(rows)
    print(f"  manifest entries: {len(entries)}")

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
        "fired_rule_ids": fired_ids,
        "errored_rule_ids": errored_ids,
        "rules_total": len(results),
        "original_count": original_count,
        "corrupted_count": len(rows),
    }


def main():
    safety_check()
    out_results = []
    for i, fn in enumerate(EXTRA_PROBES, start=200):
        try:
            out_results.append(run_probe(i, fn))
        except Exception as exc:
            import traceback
            traceback.print_exc()
            out_results.append({"probe": i, "scenario": fn.__name__, "error": str(exc)})
        finally:
            cleanup_shadow()

    out = {
        "spec": SPEC_NAME,
        "shadow_table": SHADOW_FQN,
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "probes": out_results,
    }
    out_path = PROJECT_ROOT / "governance/chaos-manifests/silver-base-bea-rpp-extra-probes.json"
    out_path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"\nExtra probe matrix written: {out_path}")

    print("\n" + "=" * 72)
    print("EXTRA PROBE SUMMARY")
    print("=" * 72)
    for p in out_results:
        if "error" in p:
            print(f"{p['probe']:>3}  {p['scenario']:<48}  ERROR  {p['error']}")
            continue
        print(
            f"{p['probe']:>3}  {p['scenario']:<48}  "
            f"{len(p['fired_rule_ids']):<4}  "
            f"{', '.join(p['fired_rule_ids']) or '(none)'}"
        )


if __name__ == "__main__":
    main()
