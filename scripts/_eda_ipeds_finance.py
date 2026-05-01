"""Full EDA pass against bronze.ipeds_finance for spec full-pipeline-ipeds-finance v1.3.

Covers EDA Reqs 2-7 plus distribution profiling for downstream P1 thresholds.
Outputs structured JSON to stdout for the markdown report writer to assemble.

Usage:
    uv run python scripts/_eda_ipeds_finance.py
"""

from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import brightsmith.config

brightsmith.config.configure(
    project_root=PROJECT_ROOT,
    require_human_approval=False,
)

import duckdb
from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb


def quantiles(values, qs=(0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)):
    """Compute requested quantiles from a list of numeric values, ignoring None."""
    nums = sorted(v for v in values if v is not None)
    if not nums:
        return {f"P{int(q*100)}": None for q in qs} | {"min": None, "max": None, "n": 0}
    out = {}
    for q in qs:
        # nearest-rank
        rank = max(0, min(len(nums) - 1, int(q * (len(nums) - 1))))
        out[f"P{int(q*100)}"] = nums[rank]
    out["min"] = nums[0]
    out["max"] = nums[-1]
    out["n"] = len(nums)
    return out


def fmt_money(v):
    if v is None:
        return "—"
    if abs(v) >= 1e9:
        return f"${v/1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.2f}M"
    if abs(v) >= 1e3:
        return f"${v/1e3:.1f}K"
    return f"${v:.2f}"


def fmt_num(v, prec=2):
    if v is None:
        return "—"
    return f"{v:,.{prec}f}"


def main() -> int:
    catalog = get_catalog(
        brightsmith.config.WAREHOUSE_PATH,
        brightsmith.config.CATALOG_PATH,
    )
    table = catalog.load_table("bronze.ipeds_finance")
    rows = read_with_duckdb(table)
    print(f"# bronze.ipeds_finance row count = {len(rows)}", file=sys.stderr)

    by_form: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_form[r["report_form"]].append(r)

    report = {
        "row_count": len(rows),
        "form_mix": {f: len(rs) for f, rs in by_form.items()},
        "distributions": {},
        "completeness": {},
        "per_fte_preview": {},
        "year_alignment": {},
        "filter_coverage": {},
        "form_mix_diagnosis": {},
        "imputation_prevalence": {},
        "anomalies": [],
    }

    # =====================================================================
    # EDA Req 3 — Distribution shapes
    # =====================================================================
    target_fields = [
        "instruction_expenses",
        "institutional_support_expenses",
        "endowment_value",
        "total_fte_enrollment",
    ]
    for field in target_fields:
        all_vals = [r[field] for r in rows]
        nonnull_n = sum(1 for v in all_vals if v is not None)
        zero_n = sum(1 for v in all_vals if v is not None and v == 0)
        report["distributions"][field] = {
            "overall": quantiles(all_vals),
            "null_count": len(all_vals) - nonnull_n,
            "null_rate": round((len(all_vals) - nonnull_n) / len(all_vals), 4),
            "zero_count": zero_n,
            "by_form": {
                form: {
                    "stats": quantiles([r[field] for r in rs]),
                    "null_count": sum(1 for r in rs if r[field] is None),
                    "null_rate": round(
                        sum(1 for r in rs if r[field] is None) / len(rs), 4
                    ),
                    "zero_count": sum(
                        1 for r in rs if r[field] is not None and r[field] == 0
                    ),
                }
                for form, rs in by_form.items()
            },
        }

    # =====================================================================
    # EDA Req 6 — Per-FTE preview
    # =====================================================================
    def safe_div(num, denom):
        if num is None or denom is None or denom == 0:
            return None
        return num / denom

    inst_per_fte = []
    instsup_per_fte = []
    end_per_fte = []
    mkt_ratio = []
    fte_zero_or_null = 0
    instr_per_fte_undef = 0
    instsup_per_fte_undef = 0
    end_per_fte_undef = 0
    mkt_undef = 0

    per_fte_by_form = defaultdict(lambda: {
        "instruction_per_fte": [],
        "institutional_support_per_fte": [],
        "endowment_per_fte": [],
        "marketing_ratio": [],
    })

    for r in rows:
        fte = r["total_fte_enrollment"]
        if fte is None or fte == 0:
            fte_zero_or_null += 1

        ipf = safe_div(r["instruction_expenses"], fte)
        ispf = safe_div(r["institutional_support_expenses"], fte)
        epf = safe_div(r["endowment_value"], fte)
        mr = safe_div(r["institutional_support_expenses"], r["instruction_expenses"])

        if r["instruction_expenses"] is not None and ipf is None:
            instr_per_fte_undef += 1
        if r["institutional_support_expenses"] is not None and ispf is None:
            instsup_per_fte_undef += 1
        if r["endowment_value"] is not None and epf is None:
            end_per_fte_undef += 1
        if r["institutional_support_expenses"] is not None and r["instruction_expenses"] is not None and mr is None:
            mkt_undef += 1

        inst_per_fte.append(ipf)
        instsup_per_fte.append(ispf)
        end_per_fte.append(epf)
        mkt_ratio.append(mr)

        per_fte_by_form[r["report_form"]]["instruction_per_fte"].append(ipf)
        per_fte_by_form[r["report_form"]]["institutional_support_per_fte"].append(ispf)
        per_fte_by_form[r["report_form"]]["endowment_per_fte"].append(epf)
        per_fte_by_form[r["report_form"]]["marketing_ratio"].append(mr)

    report["per_fte_preview"] = {
        "fte_zero_or_null": fte_zero_or_null,
        "instruction_per_fte": {
            "overall": quantiles(inst_per_fte),
            "undef_count_when_input_present": instr_per_fte_undef,
            "by_form": {f: quantiles(d["instruction_per_fte"]) for f, d in per_fte_by_form.items()},
        },
        "institutional_support_per_fte": {
            "overall": quantiles(instsup_per_fte),
            "undef_count_when_input_present": instsup_per_fte_undef,
            "by_form": {f: quantiles(d["institutional_support_per_fte"]) for f, d in per_fte_by_form.items()},
        },
        "endowment_per_fte": {
            "overall": quantiles(end_per_fte),
            "undef_count_when_input_present": end_per_fte_undef,
            "by_form": {f: quantiles(d["endowment_per_fte"]) for f, d in per_fte_by_form.items()},
        },
        "marketing_ratio": {
            "overall": quantiles(mkt_ratio),
            "undef_count_when_input_present": mkt_undef,
            "by_form": {f: quantiles(d["marketing_ratio"]) for f, d in per_fte_by_form.items()},
        },
    }

    # Marketing ratio outliers (>5.0)
    mkt_over_5 = [r for r, mr in zip(rows, mkt_ratio) if mr is not None and mr > 5.0]
    mkt_over_10 = [r for r, mr in zip(rows, mkt_ratio) if mr is not None and mr > 10.0]
    report["per_fte_preview"]["marketing_ratio_over_5_count"] = len(mkt_over_5)
    report["per_fte_preview"]["marketing_ratio_over_5_by_form"] = dict(
        Counter(r["report_form"] for r in mkt_over_5)
    )
    report["per_fte_preview"]["marketing_ratio_over_10_count"] = len(mkt_over_10)
    report["per_fte_preview"]["marketing_ratio_over_10_examples"] = [
        {
            "unitid": r["unitid"],
            "name": r["institution_name"],
            "form": r["report_form"],
            "instruction": r["instruction_expenses"],
            "inst_support": r["institutional_support_expenses"],
        }
        for r in mkt_over_10[:10]
    ]

    # instruction_per_fte outliers (>$500K)
    ipf_over_500k = [r for r, v in zip(rows, inst_per_fte) if v is not None and v > 500_000]
    ipf_over_100k = [r for r, v in zip(rows, inst_per_fte) if v is not None and v > 100_000]
    report["per_fte_preview"]["instruction_per_fte_over_500K_count"] = len(ipf_over_500k)
    report["per_fte_preview"]["instruction_per_fte_over_500K_examples"] = [
        {
            "unitid": r["unitid"],
            "name": r["institution_name"],
            "form": r["report_form"],
            "instruction": r["instruction_expenses"],
            "fte": r["total_fte_enrollment"],
            "ipf": r["instruction_expenses"] / r["total_fte_enrollment"]
            if r["total_fte_enrollment"]
            else None,
        }
        for r in ipf_over_500k[:10]
    ]
    report["per_fte_preview"]["instruction_per_fte_over_100K_count"] = len(ipf_over_100k)

    # =====================================================================
    # EDA Req 4 — Filter coverage with consumable.career_outcomes
    # =====================================================================
    bronze_unitids = {r["unitid"] for r in rows}

    co_unitids = None
    # Try gold catalog first
    gold_catalog_path = PROJECT_ROOT / "data" / "gold" / "catalog.db"
    gold_warehouse_path = PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse"
    try:
        gold_cat = get_catalog(gold_warehouse_path, gold_catalog_path)
        co_table = gold_cat.load_table("consumable.career_outcomes")
        co_rows = read_with_duckdb(co_table)
        co_unitids = {r.get("unitid") for r in co_rows if r.get("unitid") is not None}
        report["filter_coverage"]["source"] = "consumable.career_outcomes via gold catalog"
        report["filter_coverage"]["co_row_count"] = len(co_rows)
    except Exception as e:
        report["filter_coverage"]["error"] = f"Could not load consumable.career_outcomes: {e!r}"
        # Fallback: try other catalog paths
        for cat_db, wh_dir in [
            (PROJECT_ROOT / "data" / "catalog.db", PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse"),
            (PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse" / "catalog.db", PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse"),
        ]:
            try:
                gold_cat = get_catalog(wh_dir, cat_db)
                co_table = gold_cat.load_table("consumable.career_outcomes")
                co_rows = read_with_duckdb(co_table)
                co_unitids = {r.get("unitid") for r in co_rows if r.get("unitid") is not None}
                report["filter_coverage"]["source"] = f"consumable.career_outcomes via {cat_db}"
                report["filter_coverage"]["co_row_count"] = len(co_rows)
                report["filter_coverage"].pop("error", None)
                break
            except Exception:
                continue

    if co_unitids is not None:
        overlap = bronze_unitids & co_unitids
        co_only = co_unitids - bronze_unitids
        bronze_only = bronze_unitids - co_unitids
        report["filter_coverage"].update({
            "bronze_distinct_unitids": len(bronze_unitids),
            "co_distinct_unitids": len(co_unitids),
            "overlap_count": len(overlap),
            "overlap_rate_of_co": round(len(overlap) / len(co_unitids), 4) if co_unitids else None,
            "overlap_rate_of_bronze": round(len(overlap) / len(bronze_unitids), 4) if bronze_unitids else None,
            "co_only_count": len(co_only),
            "bronze_only_count": len(bronze_only),
            "co_only_sample": sorted(co_only)[:20],
            "bronze_only_sample_unitids": sorted(bronze_only)[:20],
        })

    # =====================================================================
    # EDA Req 2 — EFIA year alignment / spot checks
    # =====================================================================
    spot_unitids = {
        110635: "University of California-Berkeley",
        139959: "University of Georgia",
        199193: "University of North Carolina at Chapel Hill",
        243744: "Stanford University",
        152228: "Indiana University-Bloomington",
        # F2 anchor candidate (private NFP large): Harvard 166027 or MIT 166683
        166027: "Harvard University",
        # F3 anchor candidate (large for-profit): Strayer 131520 or Grand Canyon 104717
        104717: "Grand Canyon University",
    }
    spot_check = {}
    for uid, name in spot_unitids.items():
        match = [r for r in rows if r["unitid"] == uid]
        spot_check[uid] = {
            "name": name,
            "found": bool(match),
            "row": (
                {
                    k: match[0][k]
                    for k in (
                        "report_form",
                        "fiscal_year",
                        "institution_name",
                        "instruction_expenses",
                        "institutional_support_expenses",
                        "endowment_value",
                        "total_fte_enrollment",
                    )
                }
                if match
                else None
            ),
        }
    report["year_alignment"]["spot_checks"] = spot_check

    # Aggregate FTE sanity: total FTE summed across landed rows
    total_landed_fte = sum(r["total_fte_enrollment"] or 0 for r in rows)
    report["year_alignment"]["total_landed_fte"] = total_landed_fte

    # =====================================================================
    # EDA Req 5 — Form-mix diagnosis  (HD CONTROL/OBEREG decomposition)
    # =====================================================================
    hd_zip = PROJECT_ROOT / "data" / "raw" / "ipeds_finance_cache" / "fy2022" / "HD2022.zip"
    hd_lookup = {}
    if hd_zip.exists():
        with zipfile.ZipFile(hd_zip) as zf:
            csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            with zf.open(csv_name) as fh:
                reader = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace"))
                for row in reader:
                    try:
                        uid = int(row["UNITID"])
                    except (ValueError, KeyError):
                        continue
                    hd_lookup[uid] = {
                        "control": row.get("CONTROL"),
                        "obereg": row.get("OBEREG"),
                        "hbcu": row.get("HBCU"),
                        "relaffil": row.get("RELAFFIL"),
                        "iclevel": row.get("ICLEVEL"),
                        "hloffer": row.get("HLOFFER"),
                        "closedat": row.get("CLOSEDAT"),
                    }

    # CONTROL: 1=public, 2=private NFP, 3=private FP
    # RELAFFIL: -1 or -2 = N/A (i.e. secular nonprofit), positive code = religious affiliation
    form_diag = {}
    for form, rs in by_form.items():
        ctrl_counts = Counter()
        rel_counts = {"religious": 0, "secular": 0, "unknown": 0}
        oberegs = Counter()
        for r in rs:
            hd = hd_lookup.get(r["unitid"])
            if not hd:
                rel_counts["unknown"] += 1
                continue
            ctrl_counts[hd["control"]] += 1
            oberegs[hd["obereg"]] += 1
            relaffil = hd.get("relaffil")
            try:
                rel_int = int(relaffil)
                if rel_int > 0:
                    rel_counts["religious"] += 1
                elif rel_int < 0:
                    rel_counts["secular"] += 1
                else:
                    rel_counts["unknown"] += 1
            except (ValueError, TypeError):
                rel_counts["unknown"] += 1
        form_diag[form] = {
            "n": len(rs),
            "control_breakdown": dict(ctrl_counts),
            "religious_vs_secular": rel_counts,
            "obereg_top5": dict(oberegs.most_common(5)),
        }
    report["form_mix_diagnosis"] = form_diag

    # =====================================================================
    # EDA Req 7 — Imputation flag prevalence
    # =====================================================================
    # X-prefix flag columns. Read them from the source zips.
    finance_zips = {
        "F1A": (PROJECT_ROOT / "data" / "raw" / "ipeds_finance_cache" / "fy2022" / "F2122_F1A.zip",
                {"instruction": "F1C011", "inst_support": "F1C071", "endowment": "F1H02"}),
        "F2": (PROJECT_ROOT / "data" / "raw" / "ipeds_finance_cache" / "fy2022" / "F2122_F2.zip",
               {"instruction": "F2E011", "inst_support": "F2E061", "endowment": "F2H02"}),
        "F3": (PROJECT_ROOT / "data" / "raw" / "ipeds_finance_cache" / "fy2022" / "F2122_F3.zip",
               {"instruction": "F3E011", "inst_support": "F3E03C1"}),
    }
    imp_report = {}
    for form, (zpath, cols) in finance_zips.items():
        if not zpath.exists():
            continue
        with zipfile.ZipFile(zpath) as zf:
            csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            with zf.open(csv_name) as fh:
                reader = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace"))
                fieldnames = reader.fieldnames or []
                # Find flag columns
                flag_cols = {nice: f"X{code}" for nice, code in cols.items() if f"X{code}" in fieldnames}
                if not flag_cols:
                    imp_report[form] = {"error": f"no X-flag columns found among {list(cols.values())}"}
                    continue
                flag_dist = {nice: Counter() for nice in flag_cols}
                value_present = {nice: 0 for nice in flag_cols}
                total_rows = 0
                for row in reader:
                    total_rows += 1
                    for nice, fcol in flag_cols.items():
                        flag_val = row.get(fcol, "").strip()
                        flag_dist[nice][flag_val] += 1
                        # Value-present check: corresponding numeric column not blank/sentinel
                        numeric_col = fcol[1:]  # strip X
                        v = row.get(numeric_col, "").strip()
                        if v and v not in {"-1", "-2", ".", "PrivacySuppressed"}:
                            value_present[nice] += 1
                imp_report[form] = {
                    "total_source_rows": total_rows,
                    "flag_columns": flag_cols,
                    "flag_distributions": {nice: dict(d) for nice, d in flag_dist.items()},
                    "value_present_counts": value_present,
                }
    report["imputation_prevalence"] = imp_report

    # =====================================================================
    # Per-form NULL rates (fast reference)
    # =====================================================================
    completeness = {}
    for form, rs in by_form.items():
        n = len(rs)
        completeness[form] = {
            "n": n,
            "instruction_expenses_nonnull_pct": round(
                100 * sum(1 for r in rs if r["instruction_expenses"] is not None) / n, 2
            ),
            "institutional_support_expenses_nonnull_pct": round(
                100 * sum(1 for r in rs if r["institutional_support_expenses"] is not None) / n, 2
            ),
            "endowment_value_nonnull_pct": round(
                100 * sum(1 for r in rs if r["endowment_value"] is not None) / n, 2
            ),
            "total_fte_enrollment_nonnull_pct": round(
                100 * sum(1 for r in rs if r["total_fte_enrollment"] is not None) / n, 2
            ),
        }
    report["completeness"] = completeness

    # =====================================================================
    # Coverage gap diagnosis (bonus): HD 4-year filter rejection breakdown
    # =====================================================================
    if hd_lookup:
        # Count HD rows that pass ICLEVEL=1 AND HLOFFER>=5
        hd_4yr = 0
        hd_4yr_unitids = set()
        for uid, h in hd_lookup.items():
            try:
                ic = int(h["iclevel"])
                hl = int(h["hloffer"])
                if ic == 1 and hl >= 5:
                    hd_4yr += 1
                    hd_4yr_unitids.add(uid)
            except (ValueError, TypeError):
                continue
        report["coverage_gap_diagnosis"] = {
            "hd_4yr_bachelor_unitids": hd_4yr,
            "bronze_unitids": len(bronze_unitids),
            "missing_from_bronze": len(hd_4yr_unitids - bronze_unitids),
            "missing_sample": sorted(hd_4yr_unitids - bronze_unitids)[:10],
            # Of missing, how many are closed?
            "missing_closed_count": sum(
                1
                for uid in (hd_4yr_unitids - bronze_unitids)
                if hd_lookup.get(uid, {}).get("closedat", "").strip() not in {"-2", "", "."}
            ),
        }

    print(json.dumps(report, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
