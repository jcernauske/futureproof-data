"""Independent adversarial probes against raw.onet_experience DQ rules.

NOT a chaos monkey — these are hand-crafted corruption patterns chosen by
an adversarial auditor to test specific weaknesses the existing runner
did NOT cover. Goal: find exploits that produce reasonable-looking data
that slips past the 10 rules.

Each probe materializes an in-memory DuckDB table + runs all 10 rules.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
RULES_PATH = PROJECT_ROOT / "governance" / "dq-rules" / "raw-onet-experience.json"


def load_rules():
    return json.loads(RULES_PATH.read_text())["rules"]


def make_clean_rows(n_socs: int = 878):
    """Generate clean 4-scale data for N occupations that satisfies ALL rules."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = date.today()
    rows = []
    for i in range(n_socs):
        maj = f"{11 + (i % 10):02d}"
        mid = f"{1000 + i:04d}"
        soc = f"{maj}-{mid}.00"
        scale_cats = [("RL", "2.D.1", 12), ("RW", "3.A.1", 11),
                      ("PT", "3.A.2", 9), ("OJ", "3.A.3", 9)]
        for scale, elem, ncat in scale_cats:
            per = 100.0 / ncat
            for cat in range(1, ncat + 1):
                rows.append({
                    "onet_soc_code": soc,
                    "element_id": elem,
                    "element_name": "X",
                    "scale_id": scale,
                    "category": cat,
                    "data_value": per,
                    "n": 25,
                    "standard_error": 1.0,
                    "lower_ci_bound": None,
                    "upper_ci_bound": None,
                    "recommend_suppress": "N",
                    "date": "08/2023",
                    "domain_source": "Incumbent",
                    "ingested_at": now,
                    "source_url": "u",
                    "source_method": "m",
                    "load_date": today,
                })
    return rows


def materialize(rows):
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA raw")
    con.execute("""CREATE TABLE raw.onet_experience (
        onet_soc_code VARCHAR, element_id VARCHAR, element_name VARCHAR,
        scale_id VARCHAR, category INTEGER, data_value DOUBLE, n INTEGER,
        standard_error DOUBLE, lower_ci_bound DOUBLE, upper_ci_bound DOUBLE,
        recommend_suppress VARCHAR, date VARCHAR, domain_source VARCHAR,
        ingested_at TIMESTAMP, source_url VARCHAR, source_method VARCHAR, load_date DATE)""")
    if rows:
        cols = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(cols))
        con.executemany(
            f"INSERT INTO raw.onet_experience ({', '.join(cols)}) VALUES ({placeholders})",
            [[r[c] for c in cols] for r in rows],
        )
    return con


def exec_rules(con, rules):
    verdicts = {}
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
            else:
                passed = False
            verdicts[rid] = "PASS" if passed else "FAIL"
        except Exception as e:
            verdicts[rid] = f"ERROR: {e}"
    return verdicts


def run_probe(name: str, mutate):
    rules = load_rules()
    rows = make_clean_rows()
    rows = mutate(rows)
    con = materialize(rows)
    v = exec_rules(con, rules)
    fails = [k for k, r in v.items() if r != "PASS"]
    con.close()
    print(f"\n== {name} ==")
    print(f"  rows: {len(rows)}")
    print(f"  fails: {fails}")
    return fails, len(rows)


# --- PROBES ---

def p_swap_rw_oj_element(rows):
    """ADVERSARIAL: swap element_id on all RW rows with OJ's element_id.
    Bronze rules check element_id NOT NULL but nothing binds scale_id->element_id.
    If an upstream bug swapped these, Silver's filter scale='RW' AND elem='3.A.1'
    would return 0 rows — but Bronze would pass."""
    for r in rows:
        if r["scale_id"] == "RW":
            r["element_id"] = "3.A.3"  # OJ's element_id — now mismatched
    return rows


def p_all_rw_same_category_100(rows):
    """ADVERSARIAL: all RW data concentrated in category 1 for every occupation.
    Per-occupation sum=100 still holds (1 row at 100, 10 rows at 0). But
    this is adversarial because Silver weighted-median would return cat=1 →
    tier=entry for EVERY occupation. Does Bronze detect this?"""
    for r in rows:
        if r["scale_id"] == "RW":
            r["data_value"] = 100.0 if r["category"] == 1 else 0.0
    return rows


def p_whitespace_in_soc(rows):
    """ADVERSARIAL: leading/trailing whitespace in SOC codes that got past
    _coerce_onet_soc (which strips). But what if whitespace is EMBEDDED?"""
    if rows:
        rows[0]["onet_soc_code"] = "11- 1011.00"  # space inside
    return rows


def p_soc_with_unicode_hyphen(rows):
    """ADVERSARIAL: Unicode minus-sign or en-dash instead of ASCII hyphen."""
    if rows:
        rows[0]["onet_soc_code"] = "11\u20131011.00"  # en-dash
    return rows


def p_scale_with_trailing_whitespace(rows):
    """ADVERSARIAL: scale_id 'RW ' (trailing space) — would fail IN set.
    The ingestor DOES strip, so this gets caught. Try post-ingest injection."""
    if rows:
        rows[0]["scale_id"] = "RW "
    return rows


def p_category_out_of_range_for_scale(rows):
    """ADVERSARIAL: Add an RW category=15 (RW only has 1-11). Per-scale distinct
    count rule checks COUNT(DISTINCT category)=11 — but what if I ADD cat=15
    while still having all 11? Then distinct count = 12, so rule catches.
    BUT: what if I REPLACE cat=11 with cat=15? Still 11 distinct categories,
    but 15 is garbage."""
    for r in rows:
        if r["scale_id"] == "RW" and r["category"] == 11:
            r["category"] = 15
    return rows


def p_same_cat_duplicate_but_different_category(rows):
    """ADVERSARIAL: duplicate (soc, scale, elem) with SAME category 1.
    Grain rule catches. But what if data split: two rows with cat=1 at
    50.0 each (sum=100). Grain rule counts duplicates ≥ 1 → caught.
    So I'm good. Try: two rows same soc/scale but category null... but
    category is required grain."""
    # Add a duplicate RW cat=1 row for one occupation
    first = next((r for r in rows if r["scale_id"] == "RW" and r["category"] == 1), None)
    if first:
        rows.append(dict(first))
    return rows


def p_sum_hits_exactly_100_1(rows):
    """ADVERSARIAL: craft a per-occupation RW sum of 100.1 — right at tolerance.
    Rule is ABS(sum-100) > 0.1 → strictly greater. Sum=100.1 should PASS.
    Sum=100.2 should FAIL. Let's try 100.11 to trip it just barely."""
    target_soc = "11-1000.00"
    for r in rows:
        if r["onet_soc_code"] == target_soc and r["scale_id"] == "RW":
            if r["category"] == 1:
                r["data_value"] = 9.9909 + 0.111  # make sum slightly off
    return rows


def p_sum_100_with_negative_offsets(rows):
    """ADVERSARIAL: pairs of values that cancel — some negatives, some positive,
    summing to 100. Wait, data_value rule forbids negatives. So caught by 004.
    But what if ingestor didn't coerce 'nan' properly? Real test: NaN values."""
    import math
    for r in rows:
        if r["onet_soc_code"] == "11-1000.00" and r["scale_id"] == "RW" and r["category"] == 1:
            r["data_value"] = float("nan")
    return rows


def p_valid_scale_but_wrong_element_for_scale(rows):
    """ADVERSARIAL: for one occupation, scale='RW' but element_id='2.D.1' (RL's).
    This is structurally the same as Silver would filter element_id='3.A.1' AND
    scale='RW' → occupation silently disappears from Silver. Bronze passes
    because element_id is non-null and scale is valid."""
    target = "11-1005.00"
    for r in rows:
        if r["onet_soc_code"] == target and r["scale_id"] == "RW":
            r["element_id"] = "2.D.1"
    return rows


def p_duplicate_soc_with_different_periods(rows):
    """ADVERSARIAL: Same occupation appears twice with different date values.
    Grain doesn't include date — so two rows for same (soc, elem, scale, cat)
    would trigger grain-uniqueness. But what if source gives us
    prior-year-refresh data in the same file? Each scale has only one 'year'
    at a time, so this is only a risk if O*NET ever emits an ETE diff file."""
    # Try: mix 08/2023 and 08/2024 for same occupation (no grain collision,
    # but business nonsense)
    for r in rows:
        if r["onet_soc_code"] == "11-1010.00" and r["scale_id"] == "RW" and r["category"] <= 5:
            r["date"] = "08/2024"  # newer half
        elif r["onet_soc_code"] == "11-1010.00" and r["scale_id"] == "RW":
            r["date"] = "08/2023"  # older half
    return rows


def p_recommend_suppress_all_Y(rows):
    """ADVERSARIAL: every RW row has recommend_suppress='Y'. Sum still 100.
    Spot checks in Silver will rely on this data. Bronze has no rule on
    recommend_suppress — so this quietly ships '100% suppressed' to Silver.
    Probably Silver's responsibility — check if any Bronze rule flags this."""
    for r in rows:
        if r["scale_id"] == "RW":
            r["recommend_suppress"] = "Y"
    return rows


def p_null_recommend_suppress_with_valid_data(rows):
    """ADVERSARIAL: recommend_suppress=NULL (not 'Y' or 'N'). Bronze doesn't
    guard the value. Silver's suppress_flag logic depends on this being a
    clean 'Y' or 'N'."""
    if rows:
        rows[0]["recommend_suppress"] = None
    return rows


def p_massively_inflated_row_count(rows):
    """ADVERSARIAL: What if the ingestor processes the same file twice due to
    a retry bug, producing a 2x-duplicated output? Row count rule: 30K-45K.
    2x-dup gives 72K → caught by volume rule. But 1.1x dup gives 39K → PASSES
    volume rule. Grain uniqueness catches it though — try anyway."""
    # Add ~3000 rows (one extra occupation's worth of all scales)
    extra = make_clean_rows(n_socs=70)
    # Renumber so SOCs don't collide with the clean set
    for r in extra:
        # shift SOC to unique range
        parts = r["onet_soc_code"].split("-")
        maj = parts[0]
        rest = parts[1]
        r["onet_soc_code"] = f"{int(maj)+50:02d}-{rest}"
    return rows + extra


def p_correct_total_wrong_distribution(rows):
    """ADVERSARIAL: swap RW cat=11 and cat=1 values for one occupation.
    Keeps per-(soc,scale) sum = 100. Keeps grain uniqueness. Keeps valid SOC.
    But semantically: a clerk (cat=1=None exp) now looks like senior (cat=11).
    Silver's weighted median will be WRONG. Bronze cannot detect this."""
    target = "11-1050.00"
    for r in rows:
        if r["onet_soc_code"] == target and r["scale_id"] == "RW":
            # Shuffle the percents but keep sum at 100
            # Original is uniform (100/11 each). Force skew: cat=11 gets 50, cat=1 gets 0
            if r["category"] == 11:
                r["data_value"] = 50.0
            elif r["category"] == 1:
                r["data_value"] = 0.0
            elif r["category"] == 2:
                r["data_value"] = 50.0 - 9 * (100.0/11.0)  # balance to 100
            else:
                r["data_value"] = 100.0 / 11.0
    return rows


PROBES = [
    ("P1: swap RW element_id with OJ's element_id (scale/elem mismatch)", p_swap_rw_oj_element),
    ("P2: all RW data piled in category 1 (sum=100, but distribution corrupted)", p_all_rw_same_category_100),
    ("P3: embedded whitespace inside SOC code", p_whitespace_in_soc),
    ("P4: unicode en-dash instead of ASCII hyphen in SOC", p_soc_with_unicode_hyphen),
    ("P5: post-ingest scale_id 'RW ' with trailing space", p_scale_with_trailing_whitespace),
    ("P6: RW category=15 (out of valid 1-11 range) substituted for cat=11", p_category_out_of_range_for_scale),
    ("P7: duplicate RW cat=1 row for one occupation (grain violation)", p_same_cat_duplicate_but_different_category),
    ("P8: per-occupation RW sum just over tolerance boundary", p_sum_hits_exactly_100_1),
    ("P9: NaN data_value for one RW row", p_sum_100_with_negative_offsets),
    ("P10: RW scale with wrong element_id (element='2.D.1' RL's)", p_valid_scale_but_wrong_element_for_scale),
    ("P11: mixed vintage dates within single occupation", p_duplicate_soc_with_different_periods),
    ("P12: all RW rows recommend_suppress='Y' (100% suppressed occupations)", p_recommend_suppress_all_Y),
    ("P13: null recommend_suppress", p_null_recommend_suppress_with_valid_data),
    ("P14: 8% extra duplicated rows via rerun bug (grain collision)", p_massively_inflated_row_count),
    ("P15: category values swapped within occupation (sum=100, semantic wrong)", p_correct_total_wrong_distribution),
]


def main():
    # baseline: clean synthetic
    rules = load_rules()
    clean = make_clean_rows()
    con = materialize(clean)
    v = exec_rules(con, rules)
    baseline_fails = {k for k, r in v.items() if r != "PASS"}
    con.close()
    print(f"BASELINE (clean synthetic, 878 SOCs): fails = {sorted(baseline_fails)}")

    gaps = []
    for name, mut in PROBES:
        fails, n = run_probe(name, mut)
        new = set(fails) - baseline_fails
        flipped = baseline_fails - set(fails)
        if not new and not flipped:
            print(f"  ==> NO NEW FAILS — potential gap")
            gaps.append(name)
        else:
            print(f"  ==> new fails: {sorted(new)}, flipped-to-pass: {sorted(flipped)}")

    print("\n=== ADVERSARIAL GAPS FOUND ===")
    for g in gaps:
        print(f"  - {g}")


if __name__ == "__main__":
    main()
