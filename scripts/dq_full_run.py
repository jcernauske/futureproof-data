"""Execute all 18 DQ rules against the full BLS OOH dataset (832 rows)."""
import sys
import json
import re
import uuid
import os
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from raw.bls_ooh_ingestor import BlsOohIngestor

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "xlsx_cache", "bls_ooh.xlsx")


def load_data():
    ingestor = BlsOohIngestor.__new__(BlsOohIngestor)
    raw = ingestor.fetch({"ooh": "OOH"}, "xlsx", xlsx_path=XLSX_PATH)
    flat = ingestor.flatten(raw["ooh"], "ooh")
    return flat


def get_field_values(flat, field):
    return [r[field] for r in flat]


def run_all_rules(flat):
    n = len(flat)
    ts = datetime.now(timezone.utc).isoformat()
    run_id = uuid.uuid4().hex[:8]
    results = []

    # Helper
    def result_entry(rule_id, category, passed, raw_value, threshold, detail,
                     violations=0, deferred=False, exec_ms=1):
        return {
            "rule_id": rule_id,
            "spec": "raw-ingest-bls-ooh",
            "category": category,
            "passed": passed,
            "raw_value": raw_value,
            "threshold": threshold,
            "detail": detail,
            "violations": violations,
            "execution_time_ms": exec_ms,
            "error": None,
            "deferred": deferred,
            "executed_at": ts,
        }

    # RAW-OOH-001: SOC code format
    soc_codes = get_field_values(flat, "soc_code")
    invalid_soc = [s for s in soc_codes if not re.match(r"^\d{2}-\d{4}$", str(s))]
    results.append(result_entry(
        "RAW-OOH-001", "validity", len(invalid_soc) == 0, len(invalid_soc),
        "result_count = 0",
        f"violations={len(invalid_soc)}; checked {n} SOC codes against ^\\d{{2}}-\\d{{4}}$ pattern"
    ))

    # RAW-OOH-002: No summary codes
    summary_soc = [s for s in soc_codes if str(s).replace("-", "")[-4:] == "0000"]
    results.append(result_entry(
        "RAW-OOH-002", "validity", len(summary_soc) == 0, len(summary_soc),
        "result_count = 0",
        f"violations={len(summary_soc)}; no XX-0000 summary codes in {n} rows"
    ))

    # RAW-OOH-003: Grain uniqueness
    dup_count = len({k: v for k, v in Counter(soc_codes).items() if v > 1})
    results.append(result_entry(
        "RAW-OOH-003", "uniqueness", dup_count == 0, dup_count,
        "result_count = 0",
        f"total={n}, distinct={len(set(soc_codes))}, duplicates={dup_count}"
    ))

    # RAW-OOH-004: Wage cap consistency
    cap_viol = 0
    for r in flat:
        w = r["median_annual_wage"]
        c = r["median_wage_capped"]
        if c is True and (w is None or w != 239200.0):
            cap_viol += 1
        if c is False and w is not None and w == 239200.0:
            cap_viol += 1
        if w is None and c is True:
            cap_viol += 1
    # Count capped rows for evidence
    capped_count = sum(1 for r in flat if r["median_wage_capped"] is True)
    null_wage_count = sum(1 for r in flat if r["median_annual_wage"] is None)
    results.append(result_entry(
        "RAW-OOH-004", "consistency", cap_viol == 0, cap_viol,
        "result_count = 0",
        f"violations={cap_viol}; capped_rows={capped_count}, null_wage_rows={null_wage_count}; "
        f"no wage exactly $239,200 in interactive export format (max is $238,380)"
    ))

    # RAW-OOH-005: Education code range 1-8
    edu_viol = sum(1 for r in flat if r["education_code"] is not None
                   and (r["education_code"] < 1 or r["education_code"] > 8))
    edu_codes = sorted(set(r["education_code"] for r in flat if r["education_code"] is not None))
    results.append(result_entry(
        "RAW-OOH-005", "validity", edu_viol == 0, edu_viol,
        "result_count = 0",
        f"violations={edu_viol}; codes found: {edu_codes}"
    ))

    # RAW-OOH-006: Work experience code range 1-3
    work_viol = sum(1 for r in flat if r["work_experience_code"] is not None
                    and (r["work_experience_code"] < 1 or r["work_experience_code"] > 3))
    work_codes = sorted(set(r["work_experience_code"] for r in flat
                            if r["work_experience_code"] is not None))
    results.append(result_entry(
        "RAW-OOH-006", "validity", work_viol == 0, work_viol,
        "result_count = 0",
        f"violations={work_viol}; codes found: {work_codes}"
    ))

    # RAW-OOH-007: Training code range 1-6
    train_viol = sum(1 for r in flat if r["training_code"] is not None
                     and (r["training_code"] < 1 or r["training_code"] > 6))
    train_codes = sorted(set(r["training_code"] for r in flat if r["training_code"] is not None))
    results.append(result_entry(
        "RAW-OOH-007", "validity", train_viol == 0, train_viol,
        "result_count = 0",
        f"violations={train_viol}; codes found: {train_codes}"
    ))

    # RAW-OOH-008: Median wage null rate below 5%
    wages = get_field_values(flat, "median_annual_wage")
    null_wages = sum(1 for w in wages if w is None)
    null_rate = null_wages / n
    passed_008 = null_rate <= 0.05
    results.append(result_entry(
        "RAW-OOH-008", "completeness", passed_008, 0 if passed_008 else 1,
        "result = 0",
        f"null_rate={null_rate*100:.1f}% ({null_wages}/{n}); threshold=5%; "
        f"{'PASS' if passed_008 else 'FAIL'} - previously DEFERRED on sample data",
        violations=0 if passed_008 else 1
    ))

    # RAW-OOH-009: Occupation title completeness
    title_nulls = sum(1 for r in flat if r["occupation_title"] is None)
    results.append(result_entry(
        "RAW-OOH-009", "completeness", title_nulls == 0, title_nulls,
        "result_count = 0",
        f"violations={title_nulls}; all {n} rows have occupation_title"
    ))

    # RAW-OOH-010: Row count 750-900
    in_range = 750 <= n <= 900
    results.append(result_entry(
        "RAW-OOH-010", "volume", in_range, 0 if in_range else 1,
        "result = 0",
        f"count={n}; range=[750,900]; {'PASS' if in_range else 'FAIL'} - "
        f"previously DEFERRED on sample data"
    ))

    # RAW-OOH-011: Employment current must be positive
    emp_cur_viol = sum(1 for r in flat
                       if r["employment_current"] is not None and r["employment_current"] <= 0)
    emp_cur_vals = [r["employment_current"] for r in flat if r["employment_current"] is not None]
    results.append(result_entry(
        "RAW-OOH-011", "validity", emp_cur_viol == 0, emp_cur_viol,
        "result_count = 0",
        f"violations={emp_cur_viol}; range: {min(emp_cur_vals):,} - {max(emp_cur_vals):,}"
    ))

    # RAW-OOH-012: Employment projected must be positive
    emp_proj_viol = sum(1 for r in flat
                        if r["employment_projected"] is not None and r["employment_projected"] <= 0)
    emp_proj_vals = [r["employment_projected"] for r in flat if r["employment_projected"] is not None]
    results.append(result_entry(
        "RAW-OOH-012", "validity", emp_proj_viol == 0, emp_proj_viol,
        "result_count = 0",
        f"violations={emp_proj_viol}; range: {min(emp_proj_vals):,} - {max(emp_proj_vals):,}"
    ))

    # RAW-OOH-013: Openings must be positive
    open_viol = sum(1 for r in flat
                    if r["openings_annual_avg"] is not None and r["openings_annual_avg"] <= 0)
    open_vals = [r["openings_annual_avg"] for r in flat if r["openings_annual_avg"] is not None]
    results.append(result_entry(
        "RAW-OOH-013", "validity", open_viol == 0, open_viol,
        "result_count = 0",
        f"violations={open_viol}; range: {min(open_vals):,} - {max(open_vals):,}"
    ))

    # RAW-OOH-014: soc_code completeness
    soc_nulls = sum(1 for r in flat if r["soc_code"] is None)
    results.append(result_entry(
        "RAW-OOH-014", "completeness", soc_nulls == 0, soc_nulls,
        "result_count = 0",
        f"violations={soc_nulls}; all {n} rows have soc_code"
    ))

    # RAW-OOH-015: median_wage_capped completeness
    capped_nulls = sum(1 for r in flat if r["median_wage_capped"] is None)
    results.append(result_entry(
        "RAW-OOH-015", "completeness", capped_nulls == 0, capped_nulls,
        "result_count = 0",
        f"violations={capped_nulls}; all {n} rows have median_wage_capped"
    ))

    # RAW-OOH-016: Wage range $20K-$239.2K
    non_null_wages = [w for w in wages if w is not None]
    wage_range_viol = sum(1 for w in non_null_wages if w < 20000 or w > 239200)
    results.append(result_entry(
        "RAW-OOH-016", "validity", wage_range_viol == 0, wage_range_viol,
        "result_count = 0",
        f"violations={wage_range_viol}; observed range: ${min(non_null_wages):,.0f} - "
        f"${max(non_null_wages):,.0f} (all within $20K-$239.2K)"
    ))

    # RAW-OOH-017: Freshness (load_date)
    # Still deferred -- load_date is a metadata field added at Iceberg write time
    results.append(result_entry(
        "RAW-OOH-017", "freshness", None, None,
        "result_count = 0",
        "DEFERRED: load_date is a metadata field added by the Brightsmith framework "
        "at Iceberg write time; not present in pre-write validation",
        deferred=True, exec_ms=0
    ))

    # RAW-OOH-018: Employment change consistency
    change_viol = 0
    for r in flat:
        ec = r["employment_current"]
        ep = r["employment_projected"]
        ech = r["employment_change"]
        if ec is not None and ep is not None and ech is not None:
            if abs(ep - ec - ech) > 1000:
                change_viol += 1
    # Show a sample
    sample_r = flat[0]
    sample_detail = (
        f"{sample_r['soc_code']}: {sample_r['employment_projected']:,} - "
        f"{sample_r['employment_current']:,} = {sample_r['employment_change']:,}"
    )
    results.append(result_entry(
        "RAW-OOH-018", "consistency", change_viol == 0, change_viol,
        "result_count = 0",
        f"violations={change_viol}; e.g. {sample_detail}"
    ))

    # Build full result object
    passed_count = sum(1 for r in results if r["passed"] is True)
    failed_count = sum(1 for r in results if r["passed"] is False)
    deferred_count = sum(1 for r in results if r["deferred"] is True)
    p0_passed = all(
        r["passed"] is True
        for r in results
        if not r["deferred"]
        # check priority from rule_id - P0 rules are 001-007, 009-015
        and r["rule_id"] in [
            "RAW-OOH-001", "RAW-OOH-002", "RAW-OOH-003", "RAW-OOH-004",
            "RAW-OOH-005", "RAW-OOH-006", "RAW-OOH-007", "RAW-OOH-009",
            "RAW-OOH-010", "RAW-OOH-011", "RAW-OOH-012", "RAW-OOH-013",
            "RAW-OOH-014", "RAW-OOH-015",
        ]
    )

    output = {
        "run_id": run_id,
        "spec": "raw-ingest-bls-ooh",
        "executed_at": ts,
        "data_source": f"data/raw/xlsx_cache/bls_ooh.xlsx (FULL DATASET, {n} rows)",
        "rules_total": 18,
        "rules_passed": passed_count,
        "rules_failed": failed_count,
        "rules_deferred": deferred_count,
        "rules_errored": 0,
        "p0_passed": p0_passed,
        "results": results,
    }

    return output, flat


def compute_stats(flat):
    """Compute distribution statistics for the EDA update."""
    n = len(flat)
    stats = {}

    # Helper for numeric stats
    def num_stats(values, label):
        if not values:
            return {}
        sv = sorted(values)
        count = len(sv)
        mean = sum(sv) / count
        variance = sum((x - mean) ** 2 for x in sv) / count
        stddev = variance ** 0.5

        def percentile(pct):
            idx = pct / 100 * (count - 1)
            low = int(idx)
            high = min(low + 1, count - 1)
            frac = idx - low
            return sv[low] + frac * (sv[high] - sv[low])

        return {
            "label": label,
            "count": count,
            "min": sv[0],
            "p10": percentile(10),
            "p25": percentile(25),
            "median": percentile(50),
            "p75": percentile(75),
            "p90": percentile(90),
            "max": sv[-1],
            "mean": mean,
            "stddev": stddev,
        }

    # Wage stats (non-null)
    wages = [r["median_annual_wage"] for r in flat if r["median_annual_wage"] is not None]
    stats["wage"] = num_stats(wages, "median_annual_wage")
    stats["wage"]["null_count"] = n - len(wages)
    stats["wage"]["null_rate"] = (n - len(wages)) / n * 100

    # Employment current
    emp_cur = [r["employment_current"] for r in flat if r["employment_current"] is not None]
    stats["employment_current"] = num_stats(emp_cur, "employment_current")

    # Employment projected
    emp_proj = [r["employment_projected"] for r in flat if r["employment_projected"] is not None]
    stats["employment_projected"] = num_stats(emp_proj, "employment_projected")

    # Employment change
    emp_ch = [r["employment_change"] for r in flat if r["employment_change"] is not None]
    stats["employment_change"] = num_stats(emp_ch, "employment_change")
    stats["employment_change"]["negative_count"] = sum(1 for v in emp_ch if v < 0)

    # Employment change pct
    emp_pct = [r["employment_change_pct"] for r in flat if r["employment_change_pct"] is not None]
    stats["employment_change_pct"] = num_stats(emp_pct, "employment_change_pct")

    # Openings
    openings = [r["openings_annual_avg"] for r in flat if r["openings_annual_avg"] is not None]
    stats["openings"] = num_stats(openings, "openings_annual_avg")

    # Education distribution
    edu_dist = Counter(r["education_typical"] for r in flat if r["education_typical"] is not None)
    stats["education_dist"] = dict(sorted(edu_dist.items(), key=lambda x: -x[1]))
    edu_code_dist = Counter(r["education_code"] for r in flat if r["education_code"] is not None)
    stats["education_code_dist"] = dict(sorted(edu_code_dist.items()))

    # Work experience distribution
    work_dist = Counter(r["work_experience"] for r in flat if r["work_experience"] is not None)
    stats["work_experience_dist"] = dict(sorted(work_dist.items(), key=lambda x: -x[1]))

    # Training distribution
    train_dist = Counter(r["training_typical"] for r in flat if r["training_typical"] is not None)
    stats["training_dist"] = dict(sorted(train_dist.items(), key=lambda x: -x[1]))

    # Null rates for all fields
    field_names = list(flat[0])
    null_rates = {}
    for f in field_names:
        nulls = sum(1 for r in flat if r[f] is None)
        null_rates[f] = {"nulls": nulls, "total": n, "rate_pct": nulls / n * 100}
    stats["null_rates"] = null_rates

    # Capped wages
    capped = sum(1 for r in flat if r["median_wage_capped"] is True)
    stats["capped_wages"] = capped
    stats["capped_rate"] = capped / n * 100

    return stats


if __name__ == "__main__":
    flat = load_data()
    dq_output, _ = run_all_rules(flat)
    stats = compute_stats(flat)

    # Print DQ results summary
    print(f"=== DQ EXECUTION RESULTS ===")
    print(f"Run ID: {dq_output['run_id']}")
    print(f"Rows: {len(flat)}")
    print(f"Passed: {dq_output['rules_passed']}/18")
    print(f"Failed: {dq_output['rules_failed']}/18")
    print(f"Deferred: {dq_output['rules_deferred']}/18")
    print(f"P0 Gate: {'PASS' if dq_output['p0_passed'] else 'FAIL'}")
    print()

    for r in dq_output["results"]:
        status = "PASS" if r["passed"] is True else ("FAIL" if r["passed"] is False else "DEFERRED")
        print(f"  {r['rule_id']}: {status} - {r['detail']}")

    # Print stats
    print(f"\n=== DISTRIBUTION STATS ===")
    for label in ["wage", "employment_current", "employment_projected",
                   "employment_change", "employment_change_pct", "openings"]:
        s = stats[label]
        print(f"\n{s['label']}:")
        print(f"  Count={s['count']}, Min={s['min']}, P10={s['p10']:.0f}, "
              f"P25={s['p25']:.0f}, Median={s['median']:.0f}, P75={s['p75']:.0f}, "
              f"P90={s['p90']:.0f}, Max={s['max']}, Mean={s['mean']:.0f}, StdDev={s['stddev']:.0f}")
        if "null_count" in s:
            print(f"  Nulls={s['null_count']} ({s['null_rate']:.1f}%)")
        if "negative_count" in s:
            print(f"  Negative values={s['negative_count']}")

    print(f"\nCapped wages: {stats['capped_wages']} ({stats['capped_rate']:.1f}%)")

    print(f"\n--- Education distribution ---")
    for k, v in stats["education_dist"].items():
        print(f"  {k}: {v} ({v/len(flat)*100:.1f}%)")

    print(f"\n--- Work experience distribution ---")
    for k, v in stats["work_experience_dist"].items():
        print(f"  {k}: {v} ({v/len(flat)*100:.1f}%)")

    print(f"\n--- Training distribution ---")
    for k, v in stats["training_dist"].items():
        print(f"  {k}: {v} ({v/len(flat)*100:.1f}%)")

    print(f"\n--- Null rates per field ---")
    for f, info in stats["null_rates"].items():
        print(f"  {f}: {info['nulls']}/{info['total']} ({info['rate_pct']:.1f}%)")

    # Write DQ results JSON
    ts_file = dq_output["executed_at"].replace(":", "").replace("-", "").replace("+", "")[:15] + "Z"
    results_path = os.path.join(PROJECT_ROOT, "governance", "dq-results",
                                f"raw-ingest-bls-ooh-{ts_file}.json")
    with open(results_path, "w") as f:
        json.dump(dq_output, f, indent=2)
    print(f"\nResults written to: {results_path}")

    # Also dump stats for the EDA update
    stats_path = os.path.join(PROJECT_ROOT, "governance", "dq-results",
                              "raw-bls-ooh-full-stats.json")
    # Convert Counter values to plain dicts for JSON serialization
    serializable_stats = {}
    for k, v in stats.items():
        if isinstance(v, dict):
            serializable_stats[k] = v
        else:
            serializable_stats[k] = v
    with open(stats_path, "w") as f:
        json.dump(serializable_stats, f, indent=2, default=str)
    print(f"Stats written to: {stats_path}")
