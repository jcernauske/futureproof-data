"""EDA for raw.ipeds_finance — FY23 (2022-23 provisional) cycle.

Verifies all v1.3-locked column codes, computes distributions, form mix,
HD filter coverage, and imputation prevalence on the most-recent
fully-published Finance cycle (FY23 provisional released Sep 2024).

FY24 Finance (F2324_*) is not yet released by NCES (HTTP 404 on the
bulk URLs as of the EDA run date, 2026-04-30). FY23 is the operative
target for the immediate Iceberg promote.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

CACHE = Path("/Users/jcernauske/code/bright/futureproof-data/data/raw/ipeds_finance_cache")

SENTINELS = {"", "-1", "-2", ".", "PrivacySuppressed"}


def parse_double(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "").replace("$", "")
    if s in SENTINELS:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_int(v):
    s = str(v or "").strip()
    if s in SENTINELS:
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return None


def percentile(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * (p / 100)
    f, c = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    out = {}

    # === HD2023 (HD pairs with the END-of-fiscal-year, so HD2023 → FY23) ===
    hd_rows = read_csv(CACHE / "HD2023.csv")
    print(f"HD2023: {len(hd_rows)} rows, cols sample: {list(hd_rows[0].keys())[:10]}")
    hd_lookup = {}
    iclevel_dist = Counter()
    hloffer_dist = Counter()
    for r in hd_rows:
        unitid = parse_int(r.get("UNITID"))
        ic = parse_int(r.get("ICLEVEL"))
        hl = parse_int(r.get("HLOFFER"))
        if unitid is None:
            continue
        hd_lookup[unitid] = {
            "name": r.get("INSTNM", "").strip(),
            "iclevel": ic,
            "hloffer": hl,
        }
        iclevel_dist[ic] += 1
        hloffer_dist[hl] += 1
    out["hd"] = {
        "rows": len(hd_rows),
        "iclevel_dist": dict(iclevel_dist.most_common()),
        "hloffer_dist": dict(hloffer_dist.most_common()),
    }
    filter_unitids = {u for u, h in hd_lookup.items()
                      if h["iclevel"] == 1 and isinstance(h["hloffer"], int) and h["hloffer"] >= 5}
    out["hd_filter_coverage"] = {
        "all_hd_unitids": len(hd_lookup),
        "post_filter_unitids": len(filter_unitids),
        "filter_pct": round(100 * len(filter_unitids) / len(hd_lookup), 2),
    }
    print(f"HD filter (ICLEVEL=1 AND HLOFFER>=5) keeps {len(filter_unitids)} of {len(hd_lookup)} UNITIDs")

    # === Finance forms ===
    forms = {
        "F1A": ("f2223_f1a.csv",
                {"instruction": "F1C011", "inst_support": "F1C071", "endowment": "F1H02"}),
        "F2": ("f2223_f2.csv",
               {"instruction": "F2E011", "inst_support": "F2E061", "endowment": "F2H02"}),
        "F3": ("f2223_f3.csv",
               {"instruction": "F3E011", "inst_support": "F3E03C1", "endowment": None}),
    }

    form_data = {}
    for form, (fname, cols) in forms.items():
        path = CACHE / fname
        rows = read_csv(path)
        headers = list(rows[0].keys()) if rows else []
        # Confirm column existence
        present = {k: (v in headers if v else None) for k, v in cols.items()}
        x_present = {
            "instruction_x": f"X{cols['instruction']}" in headers if cols["instruction"] else None,
            "inst_support_x": f"X{cols['inst_support']}" in headers if cols["inst_support"] else None,
            "endowment_x": f"X{cols['endowment']}" in headers if cols["endowment"] else None,
        }
        form_data[form] = {"rows": rows, "cols": cols, "present": present, "x_present": x_present}
        print(f"\n{form} ({fname}): {len(rows)} rows; col presence={present}; X-flag presence={x_present}")

    # === EFIA2023 (FTE source) ===
    efia_rows = read_csv(CACHE / "EFIA2023.csv")
    efia_headers = list(efia_rows[0].keys())
    print(f"\nEFIA2023: {len(efia_rows)} rows, columns: {efia_headers}")
    # Grain check
    efia_unitids = [parse_int(r.get("UNITID")) for r in efia_rows]
    out["efia"] = {
        "rows": len(efia_rows),
        "distinct_unitids": len(set(u for u in efia_unitids if u is not None)),
        "columns": efia_headers,
        "fteug_present": "FTEUG" in efia_headers,
        "ftegd_present": "FTEGD" in efia_headers,
        "ftedpp_present": "FTEDPP" in efia_headers,
    }
    fte_lookup = {}
    for r in efia_rows:
        u = parse_int(r.get("UNITID"))
        if u is None:
            continue
        ug = parse_double(r.get("FTEUG"))
        gd = parse_double(r.get("FTEGD"))
        dpp = parse_double(r.get("FTEDPP"))
        if ug is None and gd is None and dpp is None:
            total = None
        else:
            total = (ug or 0) + (gd or 0) + (dpp or 0)
        fte_lookup[u] = {"fte_total": total, "ug": ug, "gd": gd, "dpp": dpp}
    print(f"EFIA grain: {out['efia']['rows']} rows / {out['efia']['distinct_unitids']} distinct UNITIDs")

    # === Apply HD filter to finance forms; build flat raw rows ===
    flat = []
    form_mix = Counter()
    inst_imp_rate = defaultdict(lambda: {"total": 0, "imputed": 0, "non_null": 0})
    for form, data in form_data.items():
        rows = data["rows"]
        cols = data["cols"]
        for r in rows:
            unitid = parse_int(r.get("UNITID"))
            if unitid is None or unitid not in hd_lookup:
                continue
            hd = hd_lookup[unitid]
            if not (hd["iclevel"] == 1 and isinstance(hd["hloffer"], int) and hd["hloffer"] >= 5):
                continue
            instr = parse_double(r.get(cols["instruction"])) if cols["instruction"] else None
            inst_sup = parse_double(r.get(cols["inst_support"])) if cols["inst_support"] else None
            endow = parse_double(r.get(cols["endowment"])) if cols["endowment"] else None
            fte = fte_lookup.get(unitid, {}).get("fte_total")
            flat.append({
                "unitid": unitid,
                "form": form,
                "instruction": instr,
                "inst_support": inst_sup,
                "endowment": endow,
                "fte_total": fte,
            })
            form_mix[form] += 1
            # X-flag tracking
            for fld, ccol in [("instruction", cols["instruction"]),
                              ("inst_support", cols["inst_support"]),
                              ("endowment", cols["endowment"])]:
                if not ccol:
                    continue
                xcol = f"X{ccol}"
                v = parse_double(r.get(ccol))
                xv = (r.get(xcol) or "").strip()
                if v is not None:
                    inst_imp_rate[(form, fld)]["non_null"] += 1
                    # IPEDS imputation flag values: see https://nces.ed.gov/ipeds/
                    # Common IPEDS X codes: A=not applicable, B=institution left blank, C=analyst-corrected,
                    # G=do not know, H=value not derived, J=logical imputation, K=ratio adjustment,
                    # L=imputed using data from another source, N=not imputed (institution-reported),
                    # P=parent/child imputation, R=reported, Z=implied zero
                    # Imputation = NOT in {R, "", "N"}. R/N = institution-reported.
                    if xv and xv.upper() not in {"R", "N", ""}:
                        inst_imp_rate[(form, fld)]["imputed"] += 1
                inst_imp_rate[(form, fld)]["total"] += 1

    out["form_mix"] = dict(form_mix)
    out["total_post_filter_rows"] = len(flat)

    # === Distribution stats ===
    def stats_for(field, form_filter=None):
        vals = [row[field] for row in flat
                if row[field] is not None and (form_filter is None or row["form"] == form_filter)]
        if not vals:
            return {"n": 0}
        s = sorted(vals)
        return {
            "n": len(vals),
            "non_null_pct": round(100 * len(vals) / (len([r for r in flat if form_filter is None or r["form"] == form_filter])), 2),
            "min": s[0],
            "p5": percentile(s, 5),
            "p25": percentile(s, 25),
            "p50": percentile(s, 50),
            "p75": percentile(s, 75),
            "p95": percentile(s, 95),
            "p99": percentile(s, 99),
            "max": s[-1],
            "mean": statistics.fmean(vals),
        }

    out["distributions"] = {
        "instruction_expenses": stats_for("instruction"),
        "institutional_support_expenses": stats_for("inst_support"),
        "endowment_value": stats_for("endowment"),
        "total_fte_enrollment": stats_for("fte_total"),
    }
    out["distributions_by_form"] = {}
    for form in ["F1A", "F2", "F3"]:
        out["distributions_by_form"][form] = {
            "instruction": stats_for("instruction", form),
            "inst_support": stats_for("inst_support", form),
            "endowment": stats_for("endowment", form),
            "fte_total": stats_for("fte_total", form),
        }

    # === F3 sparseness check (Req 6) ===
    f3_rows = [r for r in flat if r["form"] == "F3"]
    out["f3_sparseness"] = {
        "rows": len(f3_rows),
        "inst_support_null_pct": round(100 * sum(1 for r in f3_rows if r["inst_support"] is None) / max(len(f3_rows), 1), 2),
        "endowment_null_pct": round(100 * sum(1 for r in f3_rows if r["endowment"] is None) / max(len(f3_rows), 1), 2),
        "instruction_null_pct": round(100 * sum(1 for r in f3_rows if r["instruction"] is None) / max(len(f3_rows), 1), 2),
        "fte_null_pct": round(100 * sum(1 for r in f3_rows if r["fte_total"] is None) / max(len(f3_rows), 1), 2),
    }

    # === Imputation prevalence (Req 7) ===
    imp_summary = {}
    for (form, fld), counts in inst_imp_rate.items():
        nn = counts["non_null"]
        imp_summary[f"{form}.{fld}"] = {
            "non_null": nn,
            "bureau_imputed": counts["imputed"],
            "imputed_pct_of_non_null": round(100 * counts["imputed"] / nn, 2) if nn else 0,
        }
    out["imputation_prevalence"] = imp_summary

    # === Spot-check 5 known institutions ===
    spot = {110635: "UC Berkeley", 139959: "U Georgia", 199193: "UNC-CH",
            243744: "Stanford", 152228: "Indiana U-Bloomington"}
    spot_results = {}
    for uid, name in spot.items():
        fr = next((r for r in flat if r["unitid"] == uid), None)
        ef = fte_lookup.get(uid)
        spot_results[uid] = {
            "name": name,
            "in_filter": fr is not None,
            "form": fr["form"] if fr else None,
            "instruction": fr["instruction"] if fr else None,
            "inst_support": fr["inst_support"] if fr else None,
            "endowment": fr["endowment"] if fr else None,
            "fte_total": fr["fte_total"] if fr else None,
            "efia_breakdown": ef,
        }
    out["spot_check"] = spot_results

    # === Save flat sample for downstream UNITID overlap ===
    flat_unitids = sorted({r["unitid"] for r in flat})
    out["flat_unitid_count"] = len(flat_unitids)
    out["flat_unitid_sample_first10"] = flat_unitids[:10]
    out["flat_unitid_sample_last10"] = flat_unitids[-10:]

    Path("/tmp/eda_finance_unitids.txt").write_text("\n".join(str(u) for u in flat_unitids))

    print("\n=== SUMMARY ===")
    print(json.dumps({k: v for k, v in out.items() if k != "spot_check"}, indent=2, default=str)[:5000])
    Path("/tmp/eda_finance_summary.json").write_text(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
